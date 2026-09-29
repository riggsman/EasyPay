from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.settlement import Settlement, SettlementLine
from app.models.tenant import Tenant
from app.models.transaction import Transaction
from app.schemas.common import SettlementProcessRequest


def _next_settlement_ref(db: Session) -> str:
    n = db.query(Settlement).count() + 1
    return f"STL-{utcnow().year}-{n:06d}"


def calculate_settlement(db: Session, tenant_id: str, period_start: datetime, period_end: datetime) -> Settlement:
    txns = (
        db.query(Transaction)
        .filter(
            Transaction.transaction_tenant_id == tenant_id,
            Transaction.status == "SETTLED",
            Transaction.settled_at >= period_start,
            Transaction.settled_at <= period_end,
        )
        .all()
    )
    gross = sum((t.amount for t in txns), Decimal("0"))
    fees = sum((t.service_fee for t in txns), Decimal("0"))
    commission = sum((t.commission_amount for t in txns), Decimal("0"))
    net = gross - commission

    settlement = Settlement(
        settlement_reference=_next_settlement_ref(db),
        tenant_id=tenant_id,
        period_start=period_start,
        period_end=period_end,
        gross_amount=gross,
        service_fees=fees,
        commission_amount=commission,
        net_amount=net,
        status="CALCULATED",
    )
    db.add(settlement)
    db.flush()

    by_geo: dict[str, list] = {}
    for t in txns:
        by_geo.setdefault(t.transaction_geographic_unit_id, []).append(t)

    for geo_id, group in by_geo.items():
        g_gross = sum((t.amount for t in group), Decimal("0"))
        g_fees = sum((t.service_fee for t in group), Decimal("0"))
        g_comm = sum((t.commission_amount for t in group), Decimal("0"))
        db.add(
            SettlementLine(
                settlement_id=settlement.settlement_id,
                geographic_unit_id=geo_id,
                transaction_count=len(group),
                gross_amount=g_gross,
                service_fees=g_fees,
                commission_amount=g_comm,
                net_amount=g_gross - g_comm,
            )
        )

    settlement.status = "PENDING_APPROVAL"
    db.commit()
    db.refresh(settlement)
    from app.realtime.publisher import publish_settlement_event

    publish_settlement_event(db, settlement, "settlement.pending_approval")
    return settlement


def approve_settlement(db: Session, settlement_id: str, approver_id: str) -> Settlement:
    s = db.get(Settlement, settlement_id)
    if not s or s.status != "PENDING_APPROVAL":
        raise HTTPException(status_code=422, detail="Settlement not pending approval")
    s.status = "APPROVED"
    s.approved_by = approver_id
    s.approved_at = utcnow()
    db.commit()
    db.refresh(s)
    from app.services.notifications.dispatcher import notify_settlement_approved

    notify_settlement_approved(db, s, approver_id)
    db.commit()
    from app.realtime.publisher import publish_settlement_event

    publish_settlement_event(db, s, "settlement.approved", {"approved_by": approver_id})
    return s


def process_settlement(
    db: Session,
    settlement_id: str,
    payout: Optional[SettlementProcessRequest] = None,
) -> Settlement:
    s = db.get(Settlement, settlement_id)
    if not s or s.status != "APPROVED":
        raise HTTPException(status_code=422, detail="Settlement must be approved first")
    s.status = "PROCESSING"
    db.flush()

    tenant = db.get(Tenant, s.tenant_id)
    method = (payout.payout_method if payout else "MOMO").upper()
    if method not in ("MOMO", "BANK", "MOBILE_MONEY"):
        raise HTTPException(status_code=422, detail="payout_method must be MOMO or BANK")
    if method == "MOBILE_MONEY":
        method = "MOMO"

    from app.services.providers.campay import CampayClient, record_intent

    client = CampayClient(db)
    external_ref = f"{s.settlement_reference}-PAYOUT"

    if method == "MOMO":
        phone = (payout.momo_number if payout else None) or (tenant.momo_number if tenant else None)
        if not phone:
            raise HTTPException(status_code=422, detail="momo_number required for MoMo payout")
        result = client.disburse(
            amount=s.net_amount,
            phone=phone,
            description=f"Settlement payout {s.settlement_reference}",
            external_reference=external_ref,
            currency=s.currency,
        )
        record_intent(
            db,
            operation="DISBURSE",
            entity_type="settlement",
            entity_id=s.settlement_id,
            tenant_id=s.tenant_id,
            amount=str(s.net_amount),
            currency=s.currency,
            destination=phone,
            result=result,
            external_reference=external_ref,
            payout_method="MOMO",
        )
        s.payout_method = "MOMO"
        s.payout_destination = phone
        s.payout_provider_reference = result.reference
        s.payout_status = result.status if result.ok else "FAILED"
        if not result.ok:
            s.status = "APPROVED"
            db.commit()
            db.refresh(s)
            raise HTTPException(status_code=502, detail=result.error or "Campay MoMo disbursement failed")
    else:
        account = (payout.bank_account_number if payout else None) or (tenant.bank_account_number if tenant else None)
        account_name = (payout.bank_account_name if payout else None) or (tenant.organization_name if tenant else "Council")
        bank_code = (payout.bank_code if payout else None) or "UNKNOWN"
        if not account:
            raise HTTPException(status_code=422, detail="bank_account_number required for bank payout")
        result = client.bank_transfer(
            amount=s.net_amount,
            account_number=account,
            account_name=account_name or "Council",
            bank_code=bank_code,
            description=f"Settlement bank payout {s.settlement_reference}",
            external_reference=external_ref,
            currency=s.currency,
        )
        record_intent(
            db,
            operation="BANK_TRANSFER",
            entity_type="settlement",
            entity_id=s.settlement_id,
            tenant_id=s.tenant_id,
            amount=str(s.net_amount),
            currency=s.currency,
            destination=account,
            result=result,
            external_reference=external_ref,
            payout_method="BANK",
        )
        s.payout_method = "BANK"
        s.payout_destination = account
        s.payout_provider_reference = result.reference
        s.payout_status = result.status if result.ok else "FAILED"
        if not result.ok:
            s.status = "APPROVED"
            db.commit()
            db.refresh(s)
            raise HTTPException(status_code=502, detail=result.error or "Campay bank transfer failed")

    s.status = "COMPLETED"
    s.processed_at = utcnow()
    db.commit()
    db.refresh(s)
    from app.realtime.publisher import publish_settlement_event

    publish_settlement_event(
        db,
        s,
        "settlement.completed",
        {"payout_method": s.payout_method, "provider_reference": s.payout_provider_reference},
    )
    return s
