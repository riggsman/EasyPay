from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import DbDep, UserDep, require_permissions
from app.models.payer import PayerGeographicHistory, ZoneChangeRequest
from app.schemas.common import (
    PayerOut,
    PayerRegisterRequest,
    ZoneChangeRequestIn,
    ZoneHistoryOut,
)
from app.services.geography import ancestry_labels
from app.services.payer import apply_zone_change, get_payer_by_user, register_payer, review_zone_change

router = APIRouter(prefix="/payers")


@router.post("/register", response_model=PayerOut)
def register(body: PayerRegisterRequest, db: DbDep):
    return register_payer(db, body)


@router.get("/me", response_model=PayerOut)
def my_profile(db: DbDep, current: UserDep):
    if current.user_type != "PAYER":
        raise HTTPException(status_code=403, detail="Payer access only")
    return get_payer_by_user(db, current.user_id)


@router.get("/me/operating-area")
def my_operating_area(db: DbDep, current: UserDep):
    payer = get_payer_by_user(db, current.user_id)
    history = (
        db.query(PayerGeographicHistory)
        .filter(PayerGeographicHistory.payer_id == payer.payer_id)
        .order_by(PayerGeographicHistory.effective_from.desc())
        .all()
    )
    ancestry = ancestry_labels(db, payer.current_geographic_unit_id) if payer.current_geographic_unit_id else None
    return {
        "payer_id": payer.payer_id,
        "current_geographic_unit_id": payer.current_geographic_unit_id,
        "tenant_id": payer.tenant_id,
        "ancestry": ancestry,
        "history": [
            ZoneHistoryOut.model_validate(h).model_dump() for h in history
        ],
    }


@router.post("/me/operating-area/change")
def change_operating_area(body: ZoneChangeRequestIn, db: DbDep, current: UserDep):
    payer = get_payer_by_user(db, current.user_id)
    result = apply_zone_change(db, payer, body, current.user_id)
    if result.get("mode") == "APPROVAL_REQUIRED":
        req = result["request"]
        return {
            "mode": "APPROVAL_REQUIRED",
            "status": req.status,
            "zone_change_request_id": req.zone_change_request_id,
            "message": "Change request submitted for review",
        }
    return {
        "mode": "IMMEDIATE",
        "status": "ACTIVE",
        "payer": PayerOut.model_validate(result["payer"]).model_dump(),
        "ancestry": result.get("ancestry"),
    }


@router.get("/zone-change-requests")
def list_zone_requests(db: DbDep, current = Depends(require_permissions("zone_changes:review"))):
    q = db.query(ZoneChangeRequest)
    if current.user_type != "PLATFORM_ADMIN" and current.tenant_id:
        q = q.filter(ZoneChangeRequest.to_tenant_id == current.tenant_id)
    return q.order_by(ZoneChangeRequest.created_at.desc()).all()


@router.post("/zone-change-requests/{request_id}/review")
def review_request(request_id: str, approve: bool, db: DbDep, notes: str | None = None, current = Depends(require_permissions("zone_changes:review"))):
    req = review_zone_change(db, request_id, approve, current.user_id, notes)
    return {"status": req.status, "zone_change_request_id": req.zone_change_request_id}
