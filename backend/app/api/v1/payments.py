from typing import List, Optional

from fastapi import APIRouter, HTTPException

from app.core.deps import DbDep, UserDep
from app.models.receipt import Receipt
from app.models.transaction import Transaction
from app.schemas.common import (
    PaymentInitiateRequest,
    PaymentResolveRequest,
    PaymentResolveResponse,
    TransactionDetailOut,
    TransactionEventOut,
    TransactionOut,
)
from app.services.payer import get_payer_by_user
from app.services.payments import (
    complete_payment_happy_path,
    get_transaction_events,
    initiate_payment,
    resolve_payment_context,
)

router = APIRouter(prefix="/payments")


@router.post("/resolve", response_model=PaymentResolveResponse)
def resolve(body: PaymentResolveRequest, db: DbDep, current: UserDep):
    payer = get_payer_by_user(db, current.user_id)
    return resolve_payment_context(db, payer, body)


@router.post("/initiate", response_model=TransactionOut)
def initiate(body: PaymentInitiateRequest, db: DbDep, current: UserDep):
    payer = get_payer_by_user(db, current.user_id)
    return initiate_payment(db, payer, body, current.user_id)


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
    return _detail(db, txn)


@router.get("", response_model=List[TransactionOut])
def list_payments(db: DbDep, current: UserDep):
    q = db.query(Transaction)
    if current.user_type == "PAYER":
        payer = get_payer_by_user(db, current.user_id)
        q = q.filter(Transaction.payer_id == payer.payer_id)
    elif current.user_type != "PLATFORM_ADMIN":
        q = q.filter(Transaction.transaction_tenant_id == current.tenant_id)
    return q.order_by(Transaction.initiated_at.desc()).limit(100).all()


@router.get("/{transaction_id}", response_model=TransactionDetailOut)
def get_payment(transaction_id: str, db: DbDep, current: UserDep):
    txn = db.get(Transaction, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Not found")
    if current.user_type == "PAYER":
        payer = get_payer_by_user(db, current.user_id)
        if txn.payer_id != payer.payer_id:
            raise HTTPException(status_code=403, detail="Forbidden")
    elif current.user_type != "PLATFORM_ADMIN" and txn.transaction_tenant_id != current.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant isolation")
    return _detail(db, txn)


def _detail(db, txn: Transaction) -> TransactionDetailOut:
    events = get_transaction_events(db, txn.transaction_id)
    receipt = db.query(Receipt).filter(Receipt.transaction_id == txn.transaction_id).first()
    base = TransactionOut.model_validate(txn).model_dump()
    return TransactionDetailOut(
        **base,
        events=[TransactionEventOut.model_validate(e) for e in events],
        receipt_number=receipt.receipt_number if receipt else None,
        receipt_id=receipt.receipt_id if receipt else None,
    )
