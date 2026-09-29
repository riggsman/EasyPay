from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.base import new_id, utcnow
from app.models.payer import Payer, PayerGeographicHistory, ZoneChangeRequest
from app.models.tenant import Tenant
from app.models.user import Role, User, UserRole
from app.schemas.common import PayerRegisterRequest, ZoneChangeRequestIn
from app.services.audit import write_audit
from app.services.geography import ancestry_labels, get_unit, resolve_tenant_for_geographic_unit, validate_hierarchy_path


def _next_payer_ref(db: Session) -> str:
    count = db.query(Payer).count() + 1
    return f"PYR-{utcnow().year}-{count:06d}"


def register_payer(db: Session, data: PayerRegisterRequest) -> Payer:
    if data.password != data.password_confirm:
        raise HTTPException(status_code=422, detail="Passwords do not match")
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=422, detail="Username already taken")
    if data.email and db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=422, detail="Email already registered")

    validate_hierarchy_path(db, data.geographic_unit_id)
    unit = get_unit(db, data.geographic_unit_id)
    if unit.unit_type not in ("COUNCIL", "ZONE"):
        raise HTTPException(status_code=422, detail="Operating location must be a COUNCIL or ZONE")
    tenant = resolve_tenant_for_geographic_unit(db, data.geographic_unit_id)

    user = User(
        username=data.username,
        email=str(data.email) if data.email else None,
        phone_number=data.phone_number,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        user_type="PAYER",
        tenant_id=tenant.tenant_id,
    )
    db.add(user)
    db.flush()

    payer_role = db.query(Role).filter(Role.role_code == "PAYER").first()
    if payer_role:
        db.add(UserRole(user_id=user.user_id, role_id=payer_role.role_id, tenant_id=tenant.tenant_id))

    payer = Payer(
        user_id=user.user_id,
        tenant_id=tenant.tenant_id,
        payer_reference=_next_payer_ref(db),
        payer_type=data.payer_type,
        full_name=data.full_name,
        business_name=data.business_name,
        identification_type=data.identification_type,
        identification_number=data.identification_number,
        date_of_birth=data.date_of_birth,
        email=str(data.email) if data.email else None,
        phone_number=data.phone_number,
        address=data.address,
        current_geographic_unit_id=data.geographic_unit_id,
    )
    db.add(payer)
    db.flush()

    db.add(
        PayerGeographicHistory(
            payer_id=payer.payer_id,
            geographic_unit_id=data.geographic_unit_id,
            tenant_id=tenant.tenant_id,
            effective_from=utcnow(),
            change_reason="Initial registration",
            change_source="REGISTRATION",
            changed_by=user.user_id,
            status="ACTIVE",
        )
    )
    write_audit(
        db,
        actor_user_id=user.user_id,
        tenant_id=tenant.tenant_id,
        entity_type="payer",
        entity_id=payer.payer_id,
        action="REGISTER",
        after={"zone": data.geographic_unit_id, "tenant": tenant.tenant_id},
    )
    db.commit()
    db.refresh(payer)
    return payer


def get_payer_by_user(db: Session, user_id: str) -> Payer:
    payer = db.query(Payer).filter(Payer.user_id == user_id).first()
    if not payer:
        raise HTTPException(status_code=404, detail="Payer profile not found")
    return payer


def apply_zone_change(
    db: Session,
    payer: Payer,
    data: ZoneChangeRequestIn,
    actor_user_id: str,
) -> dict:
    validate_hierarchy_path(db, data.geographic_unit_id)
    unit = get_unit(db, data.geographic_unit_id)
    if unit.unit_type not in ("COUNCIL", "ZONE"):
        raise HTTPException(status_code=422, detail="New operating location must be a COUNCIL or ZONE")
    new_tenant = resolve_tenant_for_geographic_unit(db, data.geographic_unit_id)

    if data.geographic_unit_id == payer.current_geographic_unit_id:
        raise HTTPException(status_code=422, detail="Already operating in this zone")

    # Determine approval mode from current or target tenant config
    mode_tenant = db.get(Tenant, new_tenant.tenant_id) or db.get(Tenant, payer.tenant_id)
    mode = (mode_tenant.zone_change_mode if mode_tenant else "IMMEDIATE") or "IMMEDIATE"

    if mode == "APPROVAL_REQUIRED":
        req = ZoneChangeRequest(
            payer_id=payer.payer_id,
            from_geographic_unit_id=payer.current_geographic_unit_id or data.geographic_unit_id,
            to_geographic_unit_id=data.geographic_unit_id,
            from_tenant_id=payer.tenant_id,
            to_tenant_id=new_tenant.tenant_id,
            reason=data.reason,
            status="PENDING",
        )
        db.add(req)
        write_audit(
            db,
            actor_user_id=actor_user_id,
            tenant_id=payer.tenant_id,
            entity_type="zone_change_request",
            entity_id=req.zone_change_request_id,
            action="SUBMIT",
            after={"to": data.geographic_unit_id},
            reason=data.reason,
        )
        db.commit()
        db.refresh(req)
        return {"mode": "APPROVAL_REQUIRED", "request": req, "status": "PENDING"}

    _activate_zone(db, payer, data.geographic_unit_id, new_tenant.tenant_id, data.reason, actor_user_id, "PAYER")
    db.commit()
    db.refresh(payer)
    return {"mode": "IMMEDIATE", "payer": payer, "status": "ACTIVE", "ancestry": ancestry_labels(db, data.geographic_unit_id)}


def _activate_zone(
    db: Session,
    payer: Payer,
    new_geo_id: str,
    new_tenant_id: str,
    reason: Optional[str],
    actor_user_id: str,
    source: str,
) -> None:
    now = utcnow()
    open_row = (
        db.query(PayerGeographicHistory)
        .filter(PayerGeographicHistory.payer_id == payer.payer_id, PayerGeographicHistory.effective_to.is_(None))
        .first()
    )
    if open_row:
        open_row.effective_to = now
        open_row.status = "CLOSED"

    previous = payer.current_geographic_unit_id
    payer.current_geographic_unit_id = new_geo_id
    payer.tenant_id = new_tenant_id

    db.add(
        PayerGeographicHistory(
            payer_id=payer.payer_id,
            geographic_unit_id=new_geo_id,
            tenant_id=new_tenant_id,
            effective_from=now,
            change_reason=reason,
            change_source=source,
            changed_by=actor_user_id,
            status="ACTIVE",
        )
    )
    write_audit(
        db,
        actor_user_id=actor_user_id,
        tenant_id=new_tenant_id,
        entity_type="payer",
        entity_id=payer.payer_id,
        action="ZONE_CHANGE",
        before={"geographic_unit_id": previous, "tenant_id": open_row.tenant_id if open_row else None},
        after={"geographic_unit_id": new_geo_id, "tenant_id": new_tenant_id},
        reason=reason,
    )


def review_zone_change(db: Session, request_id: str, approve: bool, reviewer_id: str, notes: Optional[str] = None) -> ZoneChangeRequest:
    req = db.get(ZoneChangeRequest, request_id)
    if not req or req.status not in ("PENDING", "UNDER_REVIEW"):
        raise HTTPException(status_code=404, detail="Zone change request not found or not reviewable")
    req.reviewed_by = reviewer_id
    req.review_notes = notes
    if approve:
        payer = db.get(Payer, req.payer_id)
        if not payer:
            raise HTTPException(status_code=404, detail="Payer not found")
        _activate_zone(
            db,
            payer,
            req.to_geographic_unit_id,
            req.to_tenant_id or payer.tenant_id,
            req.reason,
            reviewer_id,
            "ADMIN_APPROVAL",
        )
        req.status = "APPROVED"
    else:
        req.status = "REJECTED"
    db.commit()
    db.refresh(req)
    return req
