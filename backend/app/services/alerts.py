"""Operational alert snapshots (pending txns, rejected, settlements awaiting approval)."""
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.settlement import Settlement
from app.models.transaction import Transaction


def compute_ops_alerts(db: Session, tenant_id: Optional[str], *, list_limit: int = 50) -> dict[str, Any]:
    pending_q = db.query(Transaction).filter(Transaction.status.in_(["INITIATED", "PROCESSING"]))
    rejected_q = db.query(Transaction).filter(Transaction.status == "REJECTED")
    settle_q = db.query(Settlement).filter(Settlement.status == "PENDING_APPROVAL")
    if tenant_id:
        pending_q = pending_q.filter(Transaction.transaction_tenant_id == tenant_id)
        rejected_q = rejected_q.filter(Transaction.transaction_tenant_id == tenant_id)
        settle_q = settle_q.filter(Settlement.tenant_id == tenant_id)
    pending = pending_q.order_by(Transaction.initiated_at.desc()).limit(list_limit).all()
    rejected = rejected_q.order_by(Transaction.initiated_at.desc()).limit(list_limit).all()
    settlements = settle_q.order_by(Settlement.created_at.desc()).limit(list_limit).all()
    return {
        "pending_transactions": len(pending),
        "rejected_transactions": len(rejected),
        "settlements_awaiting_approval": len(settlements),
        "items": {
            "pending": [
                {
                    "transaction_id": t.transaction_id,
                    "reference": t.transaction_reference,
                    "amount": str(t.total_amount),
                    "status": t.status,
                    "initiated_at": t.initiated_at.isoformat() if t.initiated_at else None,
                    "href_hint": "transactions",
                }
                for t in pending
            ],
            "rejected": [
                {
                    "transaction_id": t.transaction_id,
                    "reference": t.transaction_reference,
                    "amount": str(t.total_amount),
                    "status": t.status,
                    "initiated_at": t.initiated_at.isoformat() if t.initiated_at else None,
                    "href_hint": "transactions",
                }
                for t in rejected
            ],
            "settlements": [
                {
                    "settlement_id": s.settlement_id,
                    "reference": s.settlement_reference,
                    "net_amount": str(s.net_amount),
                    "status": s.status,
                    "href_hint": "settlements",
                }
                for s in settlements
            ],
        },
    }


def alerts_digest(snapshot: dict[str, Any]) -> str:
    return (
        f"p{snapshot.get('pending_transactions', 0)}"
        f"r{snapshot.get('rejected_transactions', 0)}"
        f"s{snapshot.get('settlements_awaiting_approval', 0)}"
    )
