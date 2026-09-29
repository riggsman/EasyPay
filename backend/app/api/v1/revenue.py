from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from decimal import Decimal

from app.core.deps import DbDep, UserDep, require_permissions
from app.models.revenue import FeeConfiguration, PaymentChannel, RevenueType
from app.schemas.common import FeeConfigCreate, RevenueTypeCreate, RevenueTypeOut
from app.services.fees import calculate_fee

router = APIRouter()


class FeePreviewIn(BaseModel):
    amount: Decimal
    revenue_type_id: Optional[str] = None
    payment_channel: Optional[str] = None
    geographic_unit_id: Optional[str] = None


@router.get("/revenue-types", response_model=List[RevenueTypeOut])
def list_revenue_types(db: DbDep, current: UserDep, tenant_id: Optional[str] = None):
    tid = tenant_id or current.tenant_id
    if current.user_type == "PAYER":
        tid = current.tenant_id
    q = db.query(RevenueType).filter(RevenueType.status == "ACTIVE")
    if tid:
        q = q.filter(RevenueType.tenant_id == tid)
    elif current.user_type != "PLATFORM_ADMIN":
        raise HTTPException(status_code=403, detail="tenant_id required")
    return q.all()


@router.post("/revenue-types", response_model=RevenueTypeOut)
def create_revenue_type(body: RevenueTypeCreate, db: DbDep, current = Depends(require_permissions("revenue:write"))):
    if not current.tenant_id and current.user_type != "PLATFORM_ADMIN":
        raise HTTPException(status_code=403, detail="No tenant context")
    tenant_id = current.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=422, detail="tenant_id required for revenue type")
    rt = RevenueType(tenant_id=tenant_id, **body.model_dump())
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return rt


@router.get("/payment-channels")
def list_channels(db: DbDep):
    return db.query(PaymentChannel).filter(PaymentChannel.status == "ACTIVE").all()


@router.post("/fees", response_model=dict)
def create_fee(body: FeeConfigCreate, db: DbDep, current = Depends(require_permissions("revenue:write"))):
    fee = FeeConfiguration(tenant_id=current.tenant_id, **body.model_dump())
    db.add(fee)
    db.commit()
    db.refresh(fee)
    return {"fee_configuration_id": fee.fee_configuration_id}


@router.post("/fees/preview")
def preview_fee(body: FeePreviewIn, db: DbDep, current: UserDep):
    fee = calculate_fee(
        db,
        amount=body.amount,
        tenant_id=current.tenant_id,
        geographic_unit_id=body.geographic_unit_id,
        revenue_type_id=body.revenue_type_id,
        payment_channel_code=body.payment_channel,
    )
    return {"service_fee": str(fee), "total": str(body.amount + fee)}
