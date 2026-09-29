"""Admin / financial operations read APIs supporting the ops console."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from app.core.deps import DbDep, UserDep, require_permissions  # noqa: F401
from app.models.notification import NotificationDelivery
from app.schemas.pagination import PaginatedResponse, paginate_query
from app.services.notifications import config as notification_config
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


@router.get("/payers", response_model=PaginatedResponse[PayerListOut])
def list_payers(
    db: DbDep,
    current=Depends(require_permissions("tenants:read", "obligations:write", "dashboards:read")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    q: Optional[str] = None,
    status: Optional[str] = None,
    tenant_id: Optional[str] = None,
    geographic_unit_id: Optional[str] = None,
):
    query = db.query(Payer)
    tid = _tenant_scope(current)
    if tid:
        query = query.filter(Payer.tenant_id == tid)
    elif tenant_id:
        query = query.filter(Payer.tenant_id == tenant_id)
    if status:
        query = query.filter(Payer.status == status)
    if geographic_unit_id:
        query = query.filter(Payer.current_geographic_unit_id == geographic_unit_id)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            (Payer.payer_reference.like(like))
            | (Payer.full_name.like(like))
            | (Payer.business_name.like(like))
            | (Payer.email.like(like))
        )
    query = query.order_by(Payer.created_at.desc())
    items, total, total_pages = paginate_query(query, page, page_size)
    return PaginatedResponse(
        items=[PayerListOut.model_validate(i) for i in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get("/collections", response_model=PaginatedResponse[CollectionOut])
def list_collections(
    db: DbDep,
    current=Depends(require_permissions("dashboards:read", "reports:read")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    status: Optional[str] = None,
    payer_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
):
    query = db.query(Collection)
    tid = _tenant_scope(current)
    if tid:
        query = query.filter(Collection.tenant_id == tid)
    elif tenant_id:
        query = query.filter(Collection.tenant_id == tenant_id)
    if status:
        query = query.filter(Collection.status == status)
    if payer_id:
        query = query.filter(Collection.payer_id == payer_id)
    if date_from:
        query = query.filter(Collection.created_at >= date_from)
    if date_to:
        query = query.filter(Collection.created_at <= date_to)
    query = query.order_by(Collection.created_at.desc())
    items, total, total_pages = paginate_query(query, page, page_size)
    return PaginatedResponse(
        items=[CollectionOut.model_validate(i) for i in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get("/audit", response_model=PaginatedResponse[AuditOut])
def list_audit(
    db: DbDep,
    current=Depends(require_permissions("dashboards:platform", "tenants:read", "reports:read")),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
):
    query = db.query(AuditEvent)
    tid = _tenant_scope(current)
    if tid:
        query = query.filter(AuditEvent.tenant_id == tid)
    if entity_type:
        query = query.filter(AuditEvent.entity_type == entity_type)
    if action:
        query = query.filter(AuditEvent.action == action)
    if date_from:
        query = query.filter(AuditEvent.created_at >= date_from)
    if date_to:
        query = query.filter(AuditEvent.created_at <= date_to)
    query = query.order_by(AuditEvent.created_at.desc())
    items, total, total_pages = paginate_query(query, page, page_size)
    return PaginatedResponse(
        items=[AuditOut.model_validate(i) for i in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get("/ledger/postings", response_model=PaginatedResponse[LedgerPostingOut])
def list_postings(
    db: DbDep,
    current=Depends(require_permissions("reports:read", "settlements:read")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    posting_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
):
    query = db.query(LedgerPosting)
    tid = _tenant_scope(current)
    if tid:
        query = query.filter(LedgerPosting.tenant_id == tid)
    if posting_type:
        query = query.filter(LedgerPosting.posting_type == posting_type)
    if date_from:
        query = query.filter(LedgerPosting.created_at >= date_from)
    if date_to:
        query = query.filter(LedgerPosting.created_at <= date_to)
    query = query.order_by(LedgerPosting.created_at.desc())
    items, total, total_pages = paginate_query(query, page, page_size)
    return PaginatedResponse(
        items=[LedgerPostingOut.model_validate(i) for i in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


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
def tenant_statement(
    db: DbDep,
    current = Depends(require_permissions("reports:read", "settlements:read")),
    tenant_id: Optional[str] = None,
):
    tid = current.tenant_id
    if current.user_type == "PLATFORM_ADMIN":
        tid = tenant_id or tid
        if not tid:
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
    pending = pending_q.order_by(Transaction.initiated_at.desc()).limit(50).all()
    rejected = rejected_q.order_by(Transaction.initiated_at.desc()).limit(50).all()
    settlements = settle_q.order_by(Settlement.created_at.desc()).limit(50).all()
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


@router.get("/search")
def global_search(
    q: str,
    db: DbDep,
    current = Depends(require_permissions("dashboards:read", "dashboards:platform", "reports:read", "tenants:read")),
    tenant_id: Optional[str] = None,
):
    term = (q or "").strip()
    if len(term) < 2:
        return {"query": term, "results": []}
    tid = _tenant_scope(current)
    if current.user_type == "PLATFORM_ADMIN" and tenant_id:
        tid = tenant_id
    like = f"%{term}%"
    results = []

    tq = db.query(Transaction).filter(
        (Transaction.transaction_reference.like(like)) | (Transaction.transaction_id.like(like))
    )
    if tid:
        tq = tq.filter(Transaction.transaction_tenant_id == tid)
    for t in tq.limit(20).all():
        results.append(
            {
                "type": "transaction",
                "id": t.transaction_id,
                "label": t.transaction_reference,
                "status": t.status,
                "amount": str(t.total_amount),
            }
        )

    pq = db.query(Payer).filter(
        (Payer.payer_reference.like(like))
        | (Payer.full_name.like(like))
        | (Payer.business_name.like(like))
        | (Payer.email.like(like))
    )
    if tid:
        pq = pq.filter(Payer.tenant_id == tid)
    for p in pq.limit(20).all():
        results.append(
            {
                "type": "payer",
                "id": p.payer_id,
                "label": p.business_name or p.full_name,
                "status": p.status,
                "reference": p.payer_reference,
            }
        )

    from app.models.receipt import Receipt

    rq = db.query(Receipt).filter((Receipt.receipt_number.like(like)) | (Receipt.verification_token.like(like)))
    if tid:
        rq = rq.filter(Receipt.tenant_id == tid)
    for r in rq.limit(20).all():
        results.append(
            {
                "type": "receipt",
                "id": r.receipt_id,
                "label": r.receipt_number,
                "status": r.status,
                "amount": str(r.total_amount),
            }
        )

    sq = db.query(Settlement).filter(
        (Settlement.settlement_reference.like(like)) | (Settlement.settlement_id.like(like))
    )
    if tid:
        sq = sq.filter(Settlement.tenant_id == tid)
    for s in sq.limit(20).all():
        results.append(
            {
                "type": "settlement",
                "id": s.settlement_id,
                "label": s.settlement_reference,
                "status": s.status,
                "amount": str(s.net_amount),
            }
        )
    return {"query": term, "results": results}


@router.get("/drill/transaction/{transaction_id}")
def drill_transaction(transaction_id: str, db: DbDep, current: UserDep):
    """Full explainability chain for a transaction."""
    from app.models.obligation import Obligation
    from app.models.receipt import Receipt
    from app.models.revenue import RevenueType
    from app.models.tenant import Tenant
    from app.models.geography import GeographicUnit
    from app.models.transaction import TransactionEvent
    from app.models.settlement import SettlementLine
    from app.services.payer import get_payer_by_user

    txn = db.get(Transaction, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if current.user_type == "PAYER":
        payer = get_payer_by_user(db, current.user_id)
        if txn.payer_id != payer.payer_id:
            raise HTTPException(status_code=403, detail="Forbidden")
    else:
        if current.user_type != "PLATFORM_ADMIN" and not any(
            current.has_permission(c) for c in ("reports:read", "dashboards:read", "settlements:read")
        ):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        tid = _tenant_scope(current)
        if tid and txn.transaction_tenant_id != tid:
            raise HTTPException(status_code=403, detail="Tenant isolation")

    payer = db.get(Payer, txn.payer_id)
    obligation = db.get(Obligation, txn.obligation_id) if txn.obligation_id else None
    collection = db.get(Collection, txn.collection_id) if txn.collection_id else None
    revenue = db.get(RevenueType, txn.revenue_type_id) if txn.revenue_type_id else None
    tenant = db.get(Tenant, txn.transaction_tenant_id)
    geo = db.get(GeographicUnit, txn.transaction_geographic_unit_id)
    receipt = db.query(Receipt).filter(Receipt.transaction_id == txn.transaction_id).first()
    events = (
        db.query(TransactionEvent)
        .filter(TransactionEvent.transaction_id == txn.transaction_id)
        .order_by(TransactionEvent.created_at.asc())
        .all()
    )
    posting = db.query(LedgerPosting).filter(LedgerPosting.transaction_id == txn.transaction_id).first()
    entries = []
    if posting:
        entries = db.query(LedgerEntry).filter(LedgerEntry.ledger_posting_id == posting.ledger_posting_id).all()
    audits = (
        db.query(AuditEvent)
        .filter(AuditEvent.entity_type == "transaction", AuditEvent.entity_id == txn.transaction_id)
        .order_by(AuditEvent.created_at.desc())
        .all()
    )
    settlement_line = None
    settlement = None
    if txn.status == "SETTLED":
        # find a settlement covering this geo/tenant period loosely via lines
        line = (
            db.query(SettlementLine)
            .join(Settlement, Settlement.settlement_id == SettlementLine.settlement_id)
            .filter(
                Settlement.tenant_id == txn.transaction_tenant_id,
                SettlementLine.geographic_unit_id == txn.transaction_geographic_unit_id,
            )
            .order_by(Settlement.created_at.desc())
            .first()
        )
        if line:
            settlement_line = line
            settlement = db.get(Settlement, line.settlement_id)

    return {
        "chain": [
            "payer",
            "obligation",
            "collection",
            "transaction",
            "fee_commission",
            "ledger",
            "receipt",
            "settlement",
        ],
        "payer": {
            "payer_id": payer.payer_id if payer else None,
            "reference": payer.payer_reference if payer else None,
            "name": (payer.business_name or payer.full_name) if payer else None,
        },
        "obligation": {
            "obligation_id": obligation.obligation_id if obligation else None,
            "description": obligation.description if obligation else None,
            "amount": str(obligation.amount) if obligation else None,
            "balance": str(obligation.balance) if obligation else None,
            "status": obligation.status if obligation else None,
            "geographic_unit_id": obligation.geographic_unit_id if obligation else None,
        },
        "collection": {
            "collection_id": collection.collection_id if collection else None,
            "amount": str(collection.amount) if collection else None,
            "status": collection.status if collection else None,
        },
        "revenue": {
            "revenue_type_id": revenue.revenue_type_id if revenue else None,
            "code": revenue.code if revenue else None,
            "name": revenue.name if revenue else None,
        },
        "tenant": {
            "tenant_id": tenant.tenant_id if tenant else None,
            "name": tenant.organization_name if tenant else None,
        },
        "geography": {
            "geographic_unit_id": geo.geographic_unit_id if geo else None,
            "name": geo.unit_name if geo else None,
            "code": geo.unit_code if geo else None,
        },
        "transaction": {
            "transaction_id": txn.transaction_id,
            "reference": txn.transaction_reference,
            "status": txn.status,
            "amount": str(txn.amount),
            "service_fee": str(txn.service_fee),
            "commission_amount": str(txn.commission_amount),
            "total_amount": str(txn.total_amount),
            "payment_channel": txn.payment_channel,
            "initiated_at": txn.initiated_at.isoformat() if txn.initiated_at else None,
            "settled_at": txn.settled_at.isoformat() if txn.settled_at else None,
        },
        "fee_commission": {
            "service_fee": str(txn.service_fee),
            "commission_amount": str(txn.commission_amount),
            "net_to_tenant": str(txn.amount - txn.commission_amount),
        },
        "events": [
            {
                "from_status": e.from_status,
                "to_status": e.to_status,
                "note": e.note,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
        "ledger": {
            "posting_id": posting.ledger_posting_id if posting else None,
            "entries": [
                {
                    "debit": str(e.debit),
                    "credit": str(e.credit),
                    "narrative": e.narrative,
                    "account_id": e.financial_account_id,
                }
                for e in entries
            ],
        },
        "receipt": {
            "receipt_id": receipt.receipt_id if receipt else None,
            "receipt_number": receipt.receipt_number if receipt else None,
            "verification_token": receipt.verification_token if receipt else None,
            "status": receipt.status if receipt else None,
        },
        "settlement": {
            "settlement_id": settlement.settlement_id if settlement else None,
            "reference": settlement.settlement_reference if settlement else None,
            "status": settlement.status if settlement else None,
            "line_id": settlement_line.settlement_line_id if settlement_line else None,
            "line_gross": str(settlement_line.gross_amount) if settlement_line else None,
        },
        "audit": [
            {
                "action": a.action,
                "reason": a.reason,
                "actor_user_id": a.actor_user_id,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "before_json": a.before_json,
                "after_json": a.after_json,
            }
            for a in audits
        ],
    }


@router.get("/payers/{payer_id}/detail")
def payer_detail(payer_id: str, db: DbDep, current = Depends(require_permissions("tenants:read", "obligations:write", "dashboards:read"))):
    from app.models.obligation import Obligation
    from app.models.receipt import Receipt

    payer = db.get(Payer, payer_id)
    if not payer:
        raise HTTPException(status_code=404, detail="Payer not found")
    tid = _tenant_scope(current)
    if tid and payer.tenant_id != tid:
        raise HTTPException(status_code=403, detail="Tenant isolation")
    obligations = db.query(Obligation).filter(Obligation.payer_id == payer_id).order_by(Obligation.created_at.desc()).all()
    txns = db.query(Transaction).filter(Transaction.payer_id == payer_id).order_by(Transaction.initiated_at.desc()).limit(50).all()
    receipts = db.query(Receipt).filter(Receipt.payer_id == payer_id).order_by(Receipt.payment_date.desc()).limit(50).all()
    return {
        "payer": PayerListOut.model_validate(payer).model_dump(),
        "obligations": [
            {
                "obligation_id": o.obligation_id,
                "description": o.description,
                "amount": str(o.amount),
                "balance": str(o.balance),
                "status": o.status,
                "geographic_unit_id": o.geographic_unit_id,
            }
            for o in obligations
        ],
        "transactions": [
            {
                "transaction_id": t.transaction_id,
                "reference": t.transaction_reference,
                "amount": str(t.amount),
                "status": t.status,
                "geographic_unit_id": t.transaction_geographic_unit_id,
            }
            for t in txns
        ],
        "receipts": [
            {"receipt_id": r.receipt_id, "receipt_number": r.receipt_number, "total_amount": str(r.total_amount), "status": r.status}
            for r in receipts
        ],
    }


@router.get("/obligations/{obligation_id}/detail")
def obligation_detail(obligation_id: str, db: DbDep, current = Depends(require_permissions("obligations:write", "reports:read", "dashboards:read"))):
    from app.models.obligation import Obligation
    from app.models.revenue import RevenueType

    obl = db.get(Obligation, obligation_id)
    if not obl:
        raise HTTPException(status_code=404, detail="Not found")
    tid = _tenant_scope(current)
    if tid and obl.tenant_id != tid:
        raise HTTPException(status_code=403, detail="Tenant isolation")
    payer = db.get(Payer, obl.payer_id)
    revenue = db.get(RevenueType, obl.revenue_type_id)
    txns = db.query(Transaction).filter(Transaction.obligation_id == obligation_id).all()
    collections = db.query(Collection).filter(Collection.obligation_id == obligation_id).all()
    return {
        "obligation": {
            "obligation_id": obl.obligation_id,
            "description": obl.description,
            "amount": str(obl.amount),
            "balance": str(obl.balance),
            "status": obl.status,
            "tenant_id": obl.tenant_id,
            "geographic_unit_id": obl.geographic_unit_id,
        },
        "payer": {"payer_id": payer.payer_id, "name": payer.business_name or payer.full_name, "reference": payer.payer_reference} if payer else None,
        "revenue": {"name": revenue.name, "code": revenue.code} if revenue else None,
        "collections": [{"collection_id": c.collection_id, "amount": str(c.amount), "status": c.status} for c in collections],
        "transactions": [
            {"transaction_id": t.transaction_id, "reference": t.transaction_reference, "amount": str(t.amount), "status": t.status}
            for t in txns
        ],
    }


@router.get("/collections/{collection_id}/detail")
def collection_detail(collection_id: str, db: DbDep, current = Depends(require_permissions("reports:read", "dashboards:read"))):
    col = db.get(Collection, collection_id)
    if not col:
        raise HTTPException(status_code=404, detail="Not found")
    tid = _tenant_scope(current)
    if tid and col.tenant_id != tid:
        raise HTTPException(status_code=403, detail="Tenant isolation")
    txns = db.query(Transaction).filter(Transaction.collection_id == collection_id).all()
    return {
        "collection": CollectionOut.model_validate(col).model_dump(),
        "transactions": [
            {"transaction_id": t.transaction_id, "reference": t.transaction_reference, "status": t.status, "amount": str(t.amount)}
            for t in txns
        ],
    }


@router.get("/settlements/{settlement_id}/detail")
def settlement_detail(settlement_id: str, db: DbDep, current = Depends(require_permissions("settlements:read"))):
    from app.models.settlement import SettlementLine
    from app.models.geography import GeographicUnit

    s = db.get(Settlement, settlement_id)
    if not s:
        raise HTTPException(status_code=404, detail="Not found")
    tid = _tenant_scope(current)
    if tid and s.tenant_id != tid:
        raise HTTPException(status_code=403, detail="Tenant isolation")
    lines = db.query(SettlementLine).filter(SettlementLine.settlement_id == settlement_id).all()
    enriched = []
    for line in lines:
        geo = db.get(GeographicUnit, line.geographic_unit_id) if line.geographic_unit_id else None
        enriched.append(
            {
                "settlement_line_id": line.settlement_line_id,
                "geographic_unit_id": line.geographic_unit_id,
                "geographic_name": geo.unit_name if geo else None,
                "transaction_count": line.transaction_count,
                "gross_amount": str(line.gross_amount),
                "service_fees": str(line.service_fees),
                "commission_amount": str(line.commission_amount),
                "net_amount": str(line.net_amount),
            }
        )
    return {
        "settlement": {
            "settlement_id": s.settlement_id,
            "reference": s.settlement_reference,
            "status": s.status,
            "gross_amount": str(s.gross_amount),
            "service_fees": str(s.service_fees),
            "commission_amount": str(s.commission_amount),
            "net_amount": str(s.net_amount),
            "period_start": s.period_start.isoformat(),
            "period_end": s.period_end.isoformat(),
        },
        "lines": enriched,
    }


class CommissionIn(BaseModel):
    commission_type: str = "PERCENT"
    commission_value: Decimal
    revenue_type_id: Optional[str] = None


@router.post("/commissions", response_model=CommissionOut)
def create_commission(body: CommissionIn, db: DbDep, current = Depends(require_permissions("revenue:write"))):
    if not current.tenant_id:
        raise HTTPException(status_code=422, detail="tenant context required")
    row = CommissionAgreement(
        tenant_id=current.tenant_id,
        revenue_type_id=body.revenue_type_id,
        commission_type=body.commission_type,
        commission_value=body.commission_value,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


class StaffCreateIn(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    role_code: str = "TENANT_ADMIN"


@router.post("/staff-users", response_model=UserListOut)
def create_staff(body: StaffCreateIn, db: DbDep, current = Depends(require_permissions("users:write", "tenants:write", "platforms:write"))):
    from app.core.security import hash_password
    from app.models.user import UserRole

    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=422, detail="Username taken")
    tenant_id = current.tenant_id
    user = User(
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        user_type="STAFF" if body.role_code != "PLATFORM_ADMIN" else "PLATFORM_ADMIN",
        tenant_id=tenant_id,
    )
    db.add(user)
    db.flush()
    role = db.query(Role).filter(Role.role_code == body.role_code).first()
    if role:
        db.add(UserRole(user_id=user.user_id, role_id=role.role_id, tenant_id=tenant_id))
    db.commit()
    db.refresh(user)
    return user


@router.get("/exports/collections.csv")
def export_collections_csv(
    db: DbDep,
    current = Depends(require_permissions("reports:read")),
    tenant_id: Optional[str] = None,
):
    from fastapi.responses import StreamingResponse
    import io
    import csv

    tid = _tenant_scope(current)
    if current.user_type == "PLATFORM_ADMIN" and tenant_id:
        tid = tenant_id
    q = db.query(Transaction).filter(Transaction.status == "SETTLED")
    if tid:
        q = q.filter(Transaction.transaction_tenant_id == tid)
    rows = q.order_by(Transaction.settled_at.desc()).limit(2000).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "transaction_reference",
            "tenant_id",
            "geographic_unit_id",
            "amount",
            "service_fee",
            "commission",
            "total",
            "channel",
            "settled_at",
        ]
    )
    for t in rows:
        w.writerow(
            [
                t.transaction_reference,
                t.transaction_tenant_id,
                t.transaction_geographic_unit_id,
                t.amount,
                t.service_fee,
                t.commission_amount,
                t.total_amount,
                t.payment_channel,
                t.settled_at.isoformat() if t.settled_at else "",
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=collections.csv"},
    )


@router.get("/exports/collections.xlsx")
def export_collections_xlsx(
    db: DbDep,
    current = Depends(require_permissions("reports:read")),
    tenant_id: Optional[str] = None,
):
    from fastapi.responses import StreamingResponse
    import io
    from openpyxl import Workbook

    tid = _tenant_scope(current)
    if current.user_type == "PLATFORM_ADMIN" and tenant_id:
        tid = tenant_id
    q = db.query(Transaction).filter(Transaction.status == "SETTLED")
    if tid:
        q = q.filter(Transaction.transaction_tenant_id == tid)
    rows = q.order_by(Transaction.settled_at.desc()).limit(2000).all()
    wb = Workbook()
    ws = wb.active
    ws.title = "Collections"
    ws.append(
        [
            "transaction_reference",
            "tenant_id",
            "geographic_unit_id",
            "amount",
            "service_fee",
            "commission",
            "total",
            "channel",
            "settled_at",
        ]
    )
    for t in rows:
        ws.append(
            [
                t.transaction_reference,
                t.transaction_tenant_id,
                t.transaction_geographic_unit_id,
                float(t.amount),
                float(t.service_fee),
                float(t.commission_amount),
                float(t.total_amount),
                t.payment_channel,
                t.settled_at.isoformat() if t.settled_at else "",
            ]
        )
    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return StreamingResponse(
        out,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=collections.xlsx"},
    )


@router.get("/payer-statement")
def payer_statement(db: DbDep, current: UserDep):
    from app.models.receipt import Receipt
    from app.services.payer import get_payer_by_user

    if current.user_type != "PAYER":
        raise HTTPException(status_code=403, detail="Payer only")
    payer = get_payer_by_user(db, current.user_id)
    txns = (
        db.query(Transaction)
        .filter(Transaction.payer_id == payer.payer_id, Transaction.status == "SETTLED")
        .order_by(Transaction.settled_at.desc())
        .all()
    )
    receipts = db.query(Receipt).filter(Receipt.payer_id == payer.payer_id).all()
    zero = Decimal("0")
    return {
        "payer_id": payer.payer_id,
        "paid_total": str(sum((t.amount for t in txns), zero)),
        "fees_total": str(sum((t.service_fee for t in txns), zero)),
        "lines": [
            {
                "reference": t.transaction_reference,
                "date": t.settled_at.isoformat() if t.settled_at else None,
                "amount": str(t.amount),
                "fee": str(t.service_fee),
                "total": str(t.total_amount),
                "geographic_unit_id": t.transaction_geographic_unit_id,
                "receipt_number": next((r.receipt_number for r in receipts if r.transaction_id == t.transaction_id), None),
            }
            for t in txns
        ],
    }


class NotificationSettingsOut(BaseModel):
    email_enabled: bool
    sms_enabled: bool
    whatsapp_enabled: bool
    sms_master_switch: bool
    email_master_switch: bool
    whatsapp_master_switch: bool


class NotificationSettingsIn(BaseModel):
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    whatsapp_enabled: Optional[bool] = None


class NotificationDeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    notification_id: str
    tenant_id: Optional[str] = None
    channel: str
    event_type: str
    recipient: str
    subject: Optional[str] = None
    body_preview: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    created_at: object


@router.get("/notifications/settings", response_model=NotificationSettingsOut)
def get_notification_settings(db: DbDep, current=Depends(require_permissions("platforms:write", "tenants:write", "reports:read"))):
    tid = current.tenant_id if current.user_type != "PLATFORM_ADMIN" else None
    return NotificationSettingsOut(**notification_config.notification_settings_snapshot(db, tid))


@router.put("/notifications/settings", response_model=NotificationSettingsOut)
def update_notification_settings(
    body: NotificationSettingsIn,
    db: DbDep,
    current=Depends(require_permissions("platforms:write", "tenants:write")),
):
    tid = current.tenant_id if current.user_type != "PLATFORM_ADMIN" else None
    if body.email_enabled is not None:
        notification_config.upsert_channel_toggle(
            db,
            tid,
            notification_config.CONFIG_EMAIL,
            body.email_enabled,
            "Enable outbound email notifications",
        )
    if body.sms_enabled is not None:
        notification_config.upsert_channel_toggle(
            db,
            tid,
            notification_config.CONFIG_SMS,
            body.sms_enabled,
            "Enable outbound SMS notifications (requires NOTIFICATIONS_SMS_ENABLED env)",
        )
    if body.whatsapp_enabled is not None:
        notification_config.upsert_channel_toggle(
            db,
            tid,
            notification_config.CONFIG_WHATSAPP,
            body.whatsapp_enabled,
            "Enable outbound WhatsApp notifications",
        )
    db.commit()
    return NotificationSettingsOut(**notification_config.notification_settings_snapshot(db, tid))


@router.get("/notifications/delivery-log", response_model=PaginatedResponse[NotificationDeliveryOut])
def list_notification_deliveries(
    db: DbDep,
    current=Depends(require_permissions("reports:read", "dashboards:read")),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    channel: Optional[str] = None,
    status: Optional[str] = None,
    event_type: Optional[str] = None,
):
    query = db.query(NotificationDelivery)
    tid = _tenant_scope(current)
    if tid:
        query = query.filter(NotificationDelivery.tenant_id == tid)
    if channel:
        query = query.filter(NotificationDelivery.channel == channel.upper())
    if status:
        query = query.filter(NotificationDelivery.status == status.upper())
    if event_type:
        query = query.filter(NotificationDelivery.event_type == event_type)
    query = query.order_by(NotificationDelivery.created_at.desc())
    items, total, total_pages = paginate_query(query, page, page_size)
    return PaginatedResponse(
        items=[NotificationDeliveryOut.model_validate(i) for i in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )
