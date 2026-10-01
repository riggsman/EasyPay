"""Payment product chooser — council / utility / future products."""
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.deps import DbDep, UserDep, require_permissions
from app.schemas.common import ORMModel
from app.services.payment_products import (
    create_product,
    ensure_default_payment_products,
    list_admin_products,
    list_payer_products,
    product_to_dict,
    update_product,
)

router = APIRouter()


class PaymentProductCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    icon_key: str = "wallet"
    accent_color: str = "#1f6b4a"
    route_path: str = Field(..., examples=["/payer/pay/council"])
    requires_catalog: bool = False
    catalog_type: Optional[str] = None
    sort_order: int = 100
    status: str = "ACTIVE"


class PaymentProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon_key: Optional[str] = None
    accent_color: Optional[str] = None
    route_path: Optional[str] = None
    requires_catalog: Optional[bool] = None
    catalog_type: Optional[str] = None
    sort_order: Optional[int] = None
    status: Optional[str] = None


class PaymentProductOut(ORMModel):
    payment_product_id: str
    code: str
    name: str
    description: Optional[str] = None
    icon_key: str
    accent_color: str
    route_path: str
    requires_catalog: bool
    catalog_type: Optional[str] = None
    sort_order: int
    status: str
    available: bool = True
    catalog_count: int = 0


@router.get("/payment-products/chooser", response_model=List[PaymentProductOut])
def payer_chooser(db: DbDep, current: UserDep):
    """Products a payer can pick on Make Payment (ACTIVE only)."""
    ensure_default_payment_products(db)
    return [PaymentProductOut(**p) for p in list_payer_products(db)]


@router.get("/payment-products", response_model=List[PaymentProductOut])
def admin_list(db: DbDep, current=Depends(require_permissions("system:configure"))):
    ensure_default_payment_products(db)
    return [PaymentProductOut(**product_to_dict(p)) for p in list_admin_products(db)]


@router.post("/payment-products", response_model=PaymentProductOut)
def admin_create(body: PaymentProductCreate, db: DbDep, current=Depends(require_permissions("system:configure"))):
    row = create_product(db, body.model_dump(), actor_user_id=current.user_id)
    return PaymentProductOut(**product_to_dict(row))


@router.patch("/payment-products/{product_id}", response_model=PaymentProductOut)
def admin_patch(product_id: str, body: PaymentProductUpdate, db: DbDep, current=Depends(require_permissions("system:configure"))):
    row = update_product(db, product_id, body.model_dump(exclude_unset=True), actor_user_id=current.user_id)
    return PaymentProductOut(**product_to_dict(row))
