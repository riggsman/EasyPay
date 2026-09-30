from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.deps import DbDep, UserDep
from app.schemas.pagination import PaginatedResponse, paginate_query
from app.models.receipt import Receipt
from app.models.transaction import Transaction
from app.schemas.common import (
    ManualCreditRequest,
    PaymentInitiateRequest,
    PaymentResolveRequest,
    PaymentResolveResponse,
    TransactionDetailOut,
    TransactionEventOut,
    TransactionOut,
)
from app.services.payer import get_payer_by_user
from app.services.payments import (
    build_manual_credit_context,
    complete_payment_happy_path,
    get_transaction_events,
    initiate_payment,
    manual_council_credit,
    resolve_payment_context,
    retry_council_credit,
    serialize_timeline_event,
)

router = APIRouter(prefix="/payments")


def _hide_commission_for_payer(payload: dict, user_type: str) -> dict:
    """Commission is internal — never expose to payers."""
    if user_type == "PAYER":
        payload = {**payload, "commission_amount": None}
    return payload


def _transaction_out(txn: Transaction, user_type: str) -> TransactionOut:
    data = _hide_commission_for_payer(TransactionOut.model_validate(txn).model_dump(), user_type)
    return TransactionOut(**data)


@router.post("/resolve", response_model=PaymentResolveResponse)
def resolve(body: PaymentResolveRequest, db: DbDep, current: UserDep):
    payer = get_payer_by_user(db, current.user_id)
    resolved = resolve_payment_context(db, payer, body)
    data = _hide_commission_for_payer(resolved.model_dump(), current.user_type)
    return PaymentResolveResponse(**data)


@router.post("/initiate", response_model=TransactionOut)
def initiate(body: PaymentInitiateRequest, db: DbDep, current: UserDep):
    payer = get_payer_by_user(db, current.user_id)
    txn = initiate_payment(db, payer, body, current.user_id)
    return _transaction_out(txn, current.user_type)


@router.post("/{transaction_id}/confirm", response_model=TransactionDetailOut)
def confirm(transaction_id: str, db: DbDep, current: UserDep):
    txn = db.get(Transaction, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Not found")
    if current.user_type == "PAYER":
        payer = get_payer_by_user(db, current.user_id)
        if txn.payer_id != payer.payer_id:
            raise HTTPException(status_code=403, detail="Forbidden")
    txn = complete_payment_happy_path(db, transaction_id, current.user_id)
    return _detail(db, txn, current.user_type)


@router.get("", response_model=PaginatedResponse[TransactionOut])
def list_payments(
    db: DbDep,
    current: UserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    status: Optional[str] = None,
    payer_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    q: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
):
    query = db.query(Transaction)
    if current.user_type == "PAYER":
        payer = get_payer_by_user(db, current.user_id)
        query = query.filter(Transaction.payer_id == payer.payer_id)
    elif current.user_type in ("PLATFORM_ADMIN", "SUPER_ADMIN"):
        if tenant_id:
            query = query.filter(Transaction.transaction_tenant_id == tenant_id)
    else:
        query = query.filter(Transaction.transaction_tenant_id == current.tenant_id)
    if status:
        query = query.filter(Transaction.status == status)
    if payer_id and current.user_type != "PAYER":
        query = query.filter(Transaction.payer_id == payer_id)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            (Transaction.transaction_reference.like(like))
            | (Transaction.transaction_id.like(like))
            | (Transaction.payment_channel.like(like))
            | (Transaction.provider_reference.like(like))
            | (Transaction.status.like(like))
        )
    if date_from:
        query = query.filter(Transaction.initiated_at >= date_from)
    if date_to:
        query = query.filter(Transaction.initiated_at <= date_to)
    query = query.order_by(Transaction.initiated_at.desc())
    items, total, total_pages = paginate_query(query, page, page_size)
    return PaginatedResponse(
        items=[_transaction_out(i, current.user_type) for i in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get("/{transaction_id}", response_model=TransactionDetailOut)
def get_payment(transaction_id: str, db: DbDep, current: UserDep):
    txn = db.get(Transaction, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Not found")
    if current.user_type == "PAYER":
        payer = get_payer_by_user(db, current.user_id)
        if txn.payer_id != payer.payer_id:
            raise HTTPException(status_code=403, detail="Forbidden")
    elif current.user_type not in ("PLATFORM_ADMIN", "SUPER_ADMIN") and txn.transaction_tenant_id != current.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant isolation")
    return _detail(db, txn, current.user_type)


@router.get("/{transaction_id}/credit-recovery")
def credit_recovery_context(transaction_id: str, db: DbDep, current: UserDep):
    txn = _staff_txn(db, transaction_id, current)
    return build_manual_credit_context(db, txn)


@router.post("/{transaction_id}/retry-credit", response_model=TransactionDetailOut)
def retry_credit(transaction_id: str, db: DbDep, current: UserDep):
    _staff_txn(db, transaction_id, current)
    txn = retry_council_credit(db, transaction_id, current.user_id)
    return _detail(db, txn, current.user_type)


@router.post("/{transaction_id}/manual-credit", response_model=TransactionDetailOut)
def manual_credit(transaction_id: str, body: ManualCreditRequest, db: DbDep, current: UserDep):
    if current.user_type not in ("PLATFORM_ADMIN", "SUPER_ADMIN"):
        raise HTTPException(status_code=403, detail="Platform administrator only")
    _staff_txn(db, transaction_id, current)
    txn = manual_council_credit(
        db,
        transaction_id,
        actor_user_id=current.user_id,
        confirm=body.confirm,
        payout_method=body.payout_method,
        momo_number=body.momo_number,
        bank_account_number=body.bank_account_number,
        bank_account_name=body.bank_account_name,
        bank_code=body.bank_code,
        amount=body.amount,
    )
    return _detail(db, txn, current.user_type)


def _staff_txn(db, transaction_id: str, current) -> Transaction:
    txn = db.get(Transaction, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Not found")
    if current.user_type == "PAYER":
        raise HTTPException(status_code=403, detail="Staff only")
    if current.user_type not in ("PLATFORM_ADMIN", "SUPER_ADMIN") and txn.transaction_tenant_id != current.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant isolation")
    return txn


def _detail(db, txn: Transaction, user_type: str) -> TransactionDetailOut:
    from app.services.receipts_pdf import receipt_pdf_path

    events = get_transaction_events(db, txn.transaction_id, user_type=user_type)
    receipt = db.query(Receipt).filter(Receipt.transaction_id == txn.transaction_id).first()
    base = _hide_commission_for_payer(TransactionOut.model_validate(txn).model_dump(), user_type)
    recovery = None
    if user_type != "PAYER" and (
        txn.failure_reason or txn.status in ("FAILED", "REJECTED", "MANUAL_INTERVENTION")
    ):
        recovery = build_manual_credit_context(db, txn)
        if user_type not in ("PLATFORM_ADMIN", "SUPER_ADMIN"):
            # Council can see reason + retry eligibility, not full bank edit payload secrets beyond defaults
            recovery = {
                **recovery,
                "warnings": recovery.get("warnings") or [],
            }
    return TransactionDetailOut(
        **base,
        events=[TransactionEventOut(**serialize_timeline_event(e, user_type=user_type)) for e in events],
        receipt_number=receipt.receipt_number if receipt else None,
        receipt_id=receipt.receipt_id if receipt else None,
        receipt_pdf_url=receipt_pdf_path(receipt.receipt_id) if receipt else None,
        credit_recovery=recovery,
    )
