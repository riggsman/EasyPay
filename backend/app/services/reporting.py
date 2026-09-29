from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.obligation import Obligation
from app.models.transaction import Transaction
from app.schemas.common import DashboardStats


def payer_dashboard(db: Session, payer_id: str) -> DashboardStats:
    outstanding = (
        db.query(func.coalesce(func.sum(Obligation.balance), 0))
        .filter(Obligation.payer_id == payer_id, Obligation.status.in_(["DUE", "PARTIAL"]))
        .scalar()
    )
    paid = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(Transaction.payer_id == payer_id, Transaction.status == "SETTLED")
        .scalar()
    )
    return DashboardStats(
        outstanding_obligations=Decimal(str(outstanding)),
        paid_total=Decimal(str(paid)),
    )


def tenant_dashboard(db: Session, tenant_id: str) -> DashboardStats:
    start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    base = db.query(Transaction).filter(
        Transaction.transaction_tenant_id == tenant_id,
        Transaction.initiated_at >= start,
        Transaction.initiated_at < end,
    )
    all_today = base.count()
    successful = base.filter(Transaction.status.in_(["SETTLED", "CREDITED", "DEBITED"])).count()
    pending = base.filter(Transaction.status.in_(["INITIATED", "PROCESSING"])).count()
    rejected = base.filter(Transaction.status == "REJECTED").count()
    collections = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.transaction_tenant_id == tenant_id,
            Transaction.status == "SETTLED",
            Transaction.settled_at >= start,
            Transaction.settled_at < end,
        )
        .scalar()
    )
    return DashboardStats(
        collections_today=Decimal(str(collections)),
        transactions_today=all_today,
        successful_today=successful,
        pending_today=pending,
        rejected_today=rejected,
    )


def collections_report(
    db: Session,
    *,
    tenant_id: Optional[str] = None,
    geographic_unit_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> dict:
    q = db.query(Transaction).filter(Transaction.status == "SETTLED")
    if tenant_id:
        q = q.filter(Transaction.transaction_tenant_id == tenant_id)
    if geographic_unit_id:
        # Use snapshot geography — never payer current zone
        q = q.filter(Transaction.transaction_geographic_unit_id == geographic_unit_id)
    if date_from:
        q = q.filter(Transaction.settled_at >= date_from)
    if date_to:
        q = q.filter(Transaction.settled_at <= date_to)
    rows = q.all()
    gross = sum((t.amount for t in rows), Decimal("0"))
    fees = sum((t.service_fee for t in rows), Decimal("0"))
    commission = sum((t.commission_amount for t in rows), Decimal("0"))
    return {
        "transaction_count": len(rows),
        "gross_collections": str(gross),
        "service_fees": str(fees),
        "commission": str(commission),
        "net_settlement": str(gross - commission),
        "transactions": [
            {
                "transaction_id": t.transaction_id,
                "reference": t.transaction_reference,
                "tenant_id": t.transaction_tenant_id,
                "geographic_unit_id": t.transaction_geographic_unit_id,
                "amount": str(t.amount),
                "settled_at": t.settled_at.isoformat() if t.settled_at else None,
            }
            for t in rows
        ],
    }
