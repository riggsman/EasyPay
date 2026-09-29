from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.settlement import Settlement, SettlementLine
from app.models.transaction import Transaction


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

    # Group by geographic unit snapshot
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


def process_settlement(db: Session, settlement_id: str) -> Settlement:
    s = db.get(Settlement, settlement_id)
    if not s or s.status != "APPROVED":
        raise HTTPException(status_code=422, detail="Settlement must be approved first")
    s.status = "PROCESSING"
    db.flush()
    s.status = "COMPLETED"
    s.processed_at = utcnow()
    db.commit()
    db.refresh(s)
    from app.realtime.publisher import publish_settlement_event

    publish_settlement_event(db, s, "settlement.completed")
    return s
