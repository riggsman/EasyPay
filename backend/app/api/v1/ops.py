"""Admin / financial operations read APIs supporting the ops console."""
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from app.core.deps import DbDep, UserDep, require_permissions
from app.models.audit import AuditEvent
from app.models.config import SystemConfiguration
from app.models.ledger import FinancialAccount, LedgerEntry, LedgerPosting
from app.models.payer import Payer
from app.models.revenue import CommissionAgreement, FeeConfiguration
from app.models.settlement import ReconciliationRecord, Settlement
from app.models.transaction import Collection, Transaction
from app.models.user import Role, User

router = APIRouter()


class PayerListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    payer_id: str
    payer_reference: str
    full_name: str
    business_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    tenant_id: Optional[str] = None
    current_geographic_unit_id: Optional[str] = None
    status: str


class CollectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    collection_id: str
    payer_id: str
    tenant_id: str
    geographic_unit_id: str
    obligation_id: Optional[str] = None
    amount: float
    currency: str
    status: str


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    audit_event_id: str
    actor_user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    entity_type: str
    entity_id: str
    action: str
    reason: Optional[str] = None
    created_at: object


class LedgerPostingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ledger_posting_id: str
    transaction_id: Optional[str] = None
    tenant_id: Optional[str] = None
    geographic_unit_id: Optional[str] = None
    description: Optional[str] = None
    posting_type: str


class LedgerEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ledger_entry_id: str
    ledger_posting_id: str
    financial_account_id: str
    debit: float
    credit: float
    currency: str
    narrative: Optional[str] = None


class ConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    config_id: str
    tenant_id: Optional[str] = None
    config_key: str
    config_value: str
    description: Optional[str] = None


class ConfigIn(BaseModel):
    config_key: str
    config_value: str
    description: Optional[str] = None


class FeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    fee_configuration_id: str
    tenant_id: Optional[str] = None
    revenue_type_id: Optional[str] = None
    fee_type: str
    fee_value: float
    currency: str
    status: str


class CommissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    commission_agreement_id: str
    tenant_id: str
    revenue_type_id: Optional[str] = None
    commission_type: str
    commission_value: float
    status: str


class UserListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    user_type: str
    tenant_id: Optional[str] = None
    is_active: bool


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role_id: str
    role_code: str
    role_name: str
    scope: str


class StatementLine(BaseModel):
    reference: str
    date: Optional[str] = None
    description: str
    debit: str = "0"
    credit: str = "0"
    balance_effect: str


def _tenant_scope(current: UserDep) -> Optional[str]:
    if current.user_type == "PLATFORM_ADMIN":
        return None
    if not current.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context required")
    return current.tenant_id


@router.get("/payers", response_model=List[PayerListOut])
def list_payers(db: DbDep, current = Depends(require_permissions("tenants:read", "obligations:write", "dashboards:read"))):
    q = db.query(Payer)
    tid = _tenant_scope(current)
    if tid:
        q = q.filter(Payer.tenant_id == tid)
    return q.order_by(Payer.created_at.desc()).limit(200).all()


@router.get("/collections", response_model=List[CollectionOut])
def list_collections(db: DbDep, current = Depends(require_permissions("dashboards:read", "reports:read"))):
    q = db.query(Collection)
    tid = _tenant_scope(current)
    if tid:
        q = q.filter(Collection.tenant_id == tid)
    return q.order_by(Collection.created_at.desc()).limit(200).all()


@router.get("/audit", response_model=List[AuditOut])
def list_audit(
    db: DbDep,
    current = Depends(require_permissions("dashboards:platform", "tenants:read", "reports:read")),
    entity_type: Optional[str] = None,
    limit: int = Query(100, le=500),
):
    q = db.query(AuditEvent)
    tid = _tenant_scope(current)
    if tid:
        q = q.filter(AuditEvent.tenant_id == tid)
    if entity_type:
        q = q.filter(AuditEvent.entity_type == entity_type)
    return q.order_by(AuditEvent.created_at.desc()).limit(limit).all()


@router.get("/ledger/postings", response_model=List[LedgerPostingOut])
def list_postings(db: DbDep, current = Depends(require_permissions("reports:read", "settlements:read"))):
    q = db.query(LedgerPosting)
    tid = _tenant_scope(current)
    if tid:
        q = q.filter(LedgerPosting.tenant_id == tid)
    return q.order_by(LedgerPosting.created_at.desc()).limit(200).all()


@router.get("/ledger/postings/{posting_id}/entries", response_model=List[LedgerEntryOut])
def posting_entries(posting_id: str, db: DbDep, current = Depends(require_permissions("reports:read", "settlements:read"))):
    posting = db.get(LedgerPosting, posting_id)
    if not posting:
        raise HTTPException(status_code=404, detail="Posting not found")
    tid = _tenant_scope(current)
    if tid and posting.tenant_id != tid:
        raise HTTPException(status_code=403, detail="Tenant isolation")
    return db.query(LedgerEntry).filter(LedgerEntry.ledger_posting_id == posting_id).all()


@router.get("/ledger/by-transaction/{transaction_id}")
def ledger_by_transaction(transaction_id: str, db: DbDep, current = Depends(require_permissions("reports:read", "settlements:read", "dashboards:read"))):
    txn = db.get(Transaction, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    tid = _tenant_scope(current)
    if tid and txn.transaction_tenant_id != tid:
        raise HTTPException(status_code=403, detail="Tenant isolation")
    posting = db.query(LedgerPosting).filter(LedgerPosting.transaction_id == transaction_id).first()
    if not posting:
        return {"posting": None, "entries": [], "accounts": []}
    entries = db.query(LedgerEntry).filter(LedgerEntry.ledger_posting_id == posting.ledger_posting_id).all()
    accounts = {
        a.financial_account_id: a
        for a in db.query(FinancialAccount).filter(
            FinancialAccount.financial_account_id.in_([e.financial_account_id for e in entries])
        )
    }
    return {
        "posting": LedgerPostingOut.model_validate(posting).model_dump(),
        "entries": [
            {
                **LedgerEntryOut.model_validate(e).model_dump(),
                "account_code": accounts.get(e.financial_account_id).account_code if accounts.get(e.financial_account_id) else None,
                "account_name": accounts.get(e.financial_account_id).account_name if accounts.get(e.financial_account_id) else None,
            }
            for e in entries
        ],
    }


@router.get("/fees", response_model=List[FeeOut])
def list_fees(db: DbDep, current = Depends(require_permissions("revenue:write", "reports:read"))):
    q = db.query(FeeConfiguration)
    tid = _tenant_scope(current)
    if tid:
        q = q.filter(FeeConfiguration.tenant_id == tid)
    return q.order_by(FeeConfiguration.created_at.desc()).all()


@router.get("/commissions", response_model=List[CommissionOut])
def list_commissions(db: DbDep, current = Depends(require_permissions("revenue:write", "reports:read"))):
    q = db.query(CommissionAgreement)
    tid = _tenant_scope(current)
    if tid:
        q = q.filter(CommissionAgreement.tenant_id == tid)
    return q.order_by(CommissionAgreement.created_at.desc()).all()


@router.get("/staff-users", response_model=List[UserListOut])
def list_staff(db: DbDep, current = Depends(require_permissions("users:write", "tenants:read"))):
    q = db.query(User).filter(User.user_type.in_(["STAFF", "PLATFORM_ADMIN"]))
    tid = _tenant_scope(current)
    if tid:
        q = q.filter(User.tenant_id == tid)
    return q.order_by(User.created_at.desc()).all()


@router.get("/roles", response_model=List[RoleOut])
def list_roles(db: DbDep, current = Depends(require_permissions("users:write", "tenants:read"))):
    return db.query(Role).order_by(Role.role_code).all()


@router.get("/config", response_model=List[ConfigOut])
def list_config(db: DbDep, current = Depends(require_permissions("tenants:read", "platforms:write", "dashboards:platform", "reports:read"))):
    q = db.query(SystemConfiguration)
    tid = _tenant_scope(current)
    if tid:
        q = q.filter((SystemConfiguration.tenant_id == tid) | (SystemConfiguration.tenant_id.is_(None)))
    return q.order_by(SystemConfiguration.config_key).all()


@router.post("/config", response_model=ConfigOut)
def upsert_config(body: ConfigIn, db: DbDep, current = Depends(require_permissions("revenue:write", "platforms:write", "tenants:write"))):
    tid = current.tenant_id if current.user_type != "PLATFORM_ADMIN" else None
    row = (
        db.query(SystemConfiguration)
        .filter(SystemConfiguration.config_key == body.config_key, SystemConfiguration.tenant_id == tid)
        .first()
    )
    if row:
        row.config_value = body.config_value
        row.description = body.description
    else:
        row = SystemConfiguration(
            tenant_id=tid,
            config_key=body.config_key,
            config_value=body.config_value,
            description=body.description,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/reconciliation")
def list_reconciliation(db: DbDep, current = Depends(require_permissions("settlements:read", "reports:read"))):
    q = db.query(ReconciliationRecord)
    tid = _tenant_scope(current)
    if tid:
        q = q.filter(ReconciliationRecord.tenant_id == tid)
    rows = q.order_by(ReconciliationRecord.created_at.desc()).limit(200).all()
    # If empty, synthesize unmatched settled txns without completed settlement context as operational exceptions view
    if not rows:
        tq = db.query(Transaction).filter(Transaction.status == "SETTLED")
        if tid:
            tq = tq.filter(Transaction.transaction_tenant_id == tid)
        txns = tq.order_by(Transaction.settled_at.desc()).limit(50).all()
        return {
            "records": [],
            "exceptions": [
                {
                    "transaction_id": t.transaction_id,
                    "reference": t.transaction_reference,
                    "amount": str(t.amount),
                    "status": "UNMATCHED_PENDING_SETTLEMENT_LINE",
                    "settled_at": t.settled_at.isoformat() if t.settled_at else None,
                }
                for t in txns
            ],
        }
    return {"records": rows, "exceptions": []}


@router.get("/statements/tenant")
def tenant_statement(db: DbDep, current = Depends(require_permissions("reports:read", "settlements:read"))):
    tid = current.tenant_id
    if current.user_type == "PLATFORM_ADMIN" and not tid:
        # platform can pass nothing — return empty guidance
        raise HTTPException(status_code=422, detail="Select a tenant context for statements")
    if not tid:
        raise HTTPException(status_code=403, detail="Tenant context required")
    txns = (
        db.query(Transaction)
        .filter(Transaction.transaction_tenant_id == tid, Transaction.status == "SETTLED")
        .order_by(Transaction.settled_at.asc())
        .limit(200)
        .all()
    )
    settlements = (
        db.query(Settlement)
        .filter(Settlement.tenant_id == tid)
        .order_by(Settlement.created_at.desc())
        .limit(50)
        .all()
    )
    lines = []
    for t in txns:
        lines.append(
            StatementLine(
                reference=t.transaction_reference,
                date=t.settled_at.isoformat() if t.settled_at else None,
                description=f"Collection {t.payment_channel}",
                credit=str(t.amount - t.commission_amount),
                balance_effect="CREDIT",
            ).model_dump()
        )
    zero = Decimal("0")
    return {
        "tenant_id": tid,
        "gross_collections": str(sum((t.amount for t in txns), zero)),
        "service_fees": str(sum((t.service_fee for t in txns), zero)),
        "commissions": str(sum((t.commission_amount for t in txns), zero)),
        "lines": lines,
        "settlements": [
            {
                "reference": s.settlement_reference,
                "net_amount": str(s.net_amount),
                "status": s.status,
                "period_start": s.period_start.isoformat(),
                "period_end": s.period_end.isoformat(),
            }
            for s in settlements
        ],
    }


@router.get("/alerts")
def ops_alerts(db: DbDep, current = Depends(require_permissions("dashboards:read", "dashboards:platform", "settlements:read"))):
    tid = _tenant_scope(current)
    pending_q = db.query(Transaction).filter(Transaction.status.in_(["INITIATED", "PROCESSING"]))
    rejected_q = db.query(Transaction).filter(Transaction.status == "REJECTED")
    settle_q = db.query(Settlement).filter(Settlement.status == "PENDING_APPROVAL")
    if tid:
        pending_q = pending_q.filter(Transaction.transaction_tenant_id == tid)
        rejected_q = rejected_q.filter(Transaction.transaction_tenant_id == tid)
        settle_q = settle_q.filter(Settlement.tenant_id == tid)
    return {
        "pending_transactions": pending_q.count(),
        "rejected_transactions": rejected_q.count(),
        "settlements_awaiting_approval": settle_q.count(),
    }
