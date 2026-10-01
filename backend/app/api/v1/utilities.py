"""Utility service catalog (admin) + payer store + bill payments."""
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.deps import DbDep, UserDep, require_permissions
from app.models.receipt import Receipt
from app.models.transaction import Transaction
from app.schemas.common import ORMModel
from app.services.payer import get_payer_by_user
from app.services.payments import get_transaction_events, serialize_timeline_event
from app.services.utilities import (
    create_service,
    get_service,
    initiate_utility_payment,
    list_admin_services,
    list_store_services,
    quote_utility,
    service_to_dict,
    update_service,
    utility_detail_for_txn,
)

router = APIRouter()


class UtilityServiceCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    category: str = "UTILITY"
    icon_key: str = "bolt"
    accent_color: str = "#1f6b4a"
    fee_type: str = "FLAT"
    fee_value: Decimal = Decimal("500")
    currency: str = "XAF"
    accept_meter_number: bool = True
    accept_bill_number: bool = True
    sort_order: int = 100
    provider_hint: Optional[str] = None
    status: str = "ACTIVE"


class UtilityServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    icon_key: Optional[str] = None
    accent_color: Optional[str] = None
    fee_type: Optional[str] = None
    fee_value: Optional[Decimal] = None
    currency: Optional[str] = None
    accept_meter_number: Optional[bool] = None
    accept_bill_number: Optional[bool] = None
    sort_order: Optional[int] = None
    provider_hint: Optional[str] = None
    status: Optional[str] = None


class UtilityServiceOut(ORMModel):
    utility_service_id: str
    code: str
    name: str
    description: Optional[str] = None
    category: str
    icon_key: str
    accent_color: str
    fee_type: str
    fee_value: Decimal
    currency: str
    accept_meter_number: bool
    accept_bill_number: bool
    sort_order: int
    status: str
    provider_hint: Optional[str] = None


class UtilityQuoteBody(BaseModel):
    utility_service_id: str
    amount: Decimal


class UtilityPayBody(BaseModel):
    utility_service_id: str
    amount: Decimal
    meter_number: Optional[str] = None
    bill_number: Optional[str] = None
    phone_number: Optional[str] = None
    idempotency_key: str = Field(..., min_length=8)
    # Test-only simulated decline (ignored unless APP_ENV=development handled in service via force_fail flag from query — keep off by default)
    simulate_failure: bool = False


@router.get("/utility-services/store", response_model=List[UtilityServiceOut])
def store_catalog(db: DbDep, current: UserDep):
    """Active services only — cards for the payer front store."""
    return [UtilityServiceOut(**service_to_dict(s)) for s in list_store_services(db)]


@router.get("/utility-services", response_model=List[UtilityServiceOut])
def admin_list(db: DbDep, current=Depends(require_permissions("system:configure"))):
    return [UtilityServiceOut(**service_to_dict(s, include_admin=True)) for s in list_admin_services(db)]


@router.post("/utility-services", response_model=UtilityServiceOut)
def admin_create(body: UtilityServiceCreate, db: DbDep, current=Depends(require_permissions("system:configure"))):
    svc = create_service(db, body.model_dump(), actor_user_id=current.user_id)
    return UtilityServiceOut(**service_to_dict(svc, include_admin=True))


@router.get("/utility-services/{service_id}", response_model=UtilityServiceOut)
def admin_get(service_id: str, db: DbDep, current=Depends(require_permissions("system:configure"))):
    svc = get_service(db, service_id)
    return UtilityServiceOut(**service_to_dict(svc, include_admin=True))


@router.patch("/utility-services/{service_id}", response_model=UtilityServiceOut)
def admin_patch(service_id: str, body: UtilityServiceUpdate, db: DbDep, current=Depends(require_permissions("system:configure"))):
    svc = update_service(db, service_id, body.model_dump(exclude_unset=True), actor_user_id=current.user_id)
    return UtilityServiceOut(**service_to_dict(svc, include_admin=True))


@router.post("/utility-payments/quote")
def quote(body: UtilityQuoteBody, db: DbDep, current: UserDep):
    if current.user_type != "PAYER":
        # Platform can preview quotes too
        pass
    return quote_utility(db, body.utility_service_id, body.amount)


@router.post("/utility-payments/initiate")
def pay(body: UtilityPayBody, db: DbDep, current: UserDep):
    if current.user_type != "PAYER":
        raise HTTPException(status_code=403, detail="Payers only")
    payer = get_payer_by_user(db, current.user_id)
    from app.core.config import get_settings

    force_fail = bool(body.simulate_failure and get_settings().APP_ENV != "production")
    txn = initiate_utility_payment(
        db,
        payer,
        utility_service_id=body.utility_service_id,
        amount=body.amount,
        meter_number=body.meter_number,
        bill_number=body.bill_number,
        phone_number=body.phone_number,
        idempotency_key=body.idempotency_key,
        actor_user_id=current.user_id,
        force_fail=force_fail,
    )
    detail = utility_detail_for_txn(db, txn.transaction_id)
    receipt = db.query(Receipt).filter(Receipt.transaction_id == txn.transaction_id).first()
    events = get_transaction_events(db, txn.transaction_id, user_type=current.user_type)
    return {
        "transaction_id": txn.transaction_id,
        "transaction_reference": txn.transaction_reference,
        "status": txn.status,
        "product_type": txn.product_type,
        "amount": str(txn.amount),
        "service_fee": str(txn.service_fee),
        "total_amount": str(txn.total_amount),
        "currency": txn.currency,
        "failure_reason": txn.failure_reason,
        "failure_stage": txn.failure_stage,
        "utility": {
            "utility_service_id": detail.utility_service_id if detail else None,
            "service_name": detail.service_name_snapshot if detail else None,
            "service_code": detail.service_code_snapshot if detail else None,
            "reference_type": detail.reference_type if detail else None,
            "meter_number": detail.meter_number if detail else None,
            "bill_number": detail.bill_number if detail else None,
        },
        "receipt_id": receipt.receipt_id if receipt else None,
        "receipt_number": receipt.receipt_number if receipt else None,
        "receipt_pdf_url": f"/api/v1/receipts/{receipt.receipt_id}/pdf" if receipt else None,
        "events": [serialize_timeline_event(e, user_type=current.user_type) for e in events],
        "ok": txn.status == "SETTLED",
    }
