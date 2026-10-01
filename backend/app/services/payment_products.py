"""Payment product chooser catalog for the payer Make Payment hub."""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.payment_product import PaymentProduct
from app.models.utility import UtilityService
from app.services.audit import write_audit


DEFAULT_PRODUCTS = [
    {
        "code": "COUNCIL",
        "name": "Council levies",
        "description": "Pay business license, waste levy, market fees and other council obligations for your operating area.",
        "icon_key": "council",
        "accent_color": "#134832",
        "route_path": "/payer/pay/council",
        "requires_catalog": False,
        "catalog_type": None,
        "sort_order": 10,
        "status": "ACTIVE",
    },
    {
        "code": "UTILITY",
        "name": "Utility bills",
        "description": "Pay electricity, water and other utility bills with a meter or bill number.",
        "icon_key": "utility",
        "accent_color": "#2b6cb0",
        "route_path": "/payer/pay/utilities",
        "requires_catalog": True,
        "catalog_type": "UTILITY",
        "sort_order": 20,
        "status": "ACTIVE",
    },
]


def product_to_dict(row: PaymentProduct, *, available: bool = True, catalog_count: int = 0) -> dict:
    return {
        "payment_product_id": row.payment_product_id,
        "code": row.code,
        "name": row.name,
        "description": row.description,
        "icon_key": row.icon_key,
        "accent_color": row.accent_color,
        "route_path": row.route_path,
        "requires_catalog": bool(row.requires_catalog),
        "catalog_type": row.catalog_type,
        "sort_order": row.sort_order,
        "status": row.status,
        "available": available,
        "catalog_count": catalog_count,
    }


def _catalog_count(db: Session, catalog_type: Optional[str]) -> int:
    if catalog_type == "UTILITY":
        return db.query(UtilityService).filter(UtilityService.status == "ACTIVE").count()
    return 0


def ensure_default_payment_products(db: Session) -> dict:
    out = {}
    for spec in DEFAULT_PRODUCTS:
        row = db.query(PaymentProduct).filter(PaymentProduct.code == spec["code"]).first()
        if not row:
            row = PaymentProduct(**spec)
            db.add(row)
        else:
            # Keep admin edits to name/status; refresh route/catalog wiring from defaults
            row.route_path = spec["route_path"]
            row.requires_catalog = spec["requires_catalog"]
            row.catalog_type = spec["catalog_type"]
            if not row.icon_key:
                row.icon_key = spec["icon_key"]
        db.flush()
        out[spec["code"]] = row.payment_product_id
    db.commit()
    return out


def list_admin_products(db: Session) -> list[PaymentProduct]:
    return db.query(PaymentProduct).order_by(PaymentProduct.sort_order.asc(), PaymentProduct.name.asc()).all()


def list_payer_products(db: Session) -> list[dict]:
    """ACTIVE products a payer can choose, with availability based on catalogs."""
    rows = (
        db.query(PaymentProduct)
        .filter(PaymentProduct.status == "ACTIVE")
        .order_by(PaymentProduct.sort_order.asc(), PaymentProduct.name.asc())
        .all()
    )
    out = []
    for row in rows:
        count = _catalog_count(db, row.catalog_type) if row.requires_catalog else 0
        available = True
        if row.requires_catalog and count < 1:
            available = False
        # Still include unavailable catalog products so UI can explain why
        out.append(product_to_dict(row, available=available, catalog_count=count))
    return out


def get_product(db: Session, product_id: str) -> PaymentProduct:
    row = db.get(PaymentProduct, product_id)
    if not row:
        raise HTTPException(status_code=404, detail="Payment product not found")
    return row


def create_product(db: Session, data: dict, actor_user_id: Optional[str] = None) -> PaymentProduct:
    code = (data.get("code") or "").strip().upper()
    if not code:
        raise HTTPException(status_code=422, detail="code required")
    if db.query(PaymentProduct).filter(PaymentProduct.code == code).first():
        raise HTTPException(status_code=422, detail="code already exists")
    route = (data.get("route_path") or "").strip()
    if not route.startswith("/payer/"):
        raise HTTPException(status_code=422, detail="route_path must start with /payer/")
    row = PaymentProduct(
        code=code,
        name=(data.get("name") or code).strip(),
        description=data.get("description"),
        icon_key=data.get("icon_key") or "wallet",
        accent_color=data.get("accent_color") or "#1f6b4a",
        route_path=route,
        requires_catalog=bool(data.get("requires_catalog")),
        catalog_type=(data.get("catalog_type") or None),
        sort_order=int(data.get("sort_order") or 100),
        status=(data.get("status") or "ACTIVE").upper(),
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        actor_user_id=actor_user_id,
        tenant_id=None,
        entity_type="payment_product",
        entity_id=row.payment_product_id,
        action="CREATE",
        after=product_to_dict(row),
    )
    db.commit()
    db.refresh(row)
    return row


def update_product(db: Session, product_id: str, data: dict, actor_user_id: Optional[str] = None) -> PaymentProduct:
    row = get_product(db, product_id)
    before = product_to_dict(row)
    for key in ("name", "description", "icon_key", "accent_color", "catalog_type"):
        if key in data and data[key] is not None:
            setattr(row, key, data[key])
    if "route_path" in data and data["route_path"] is not None:
        route = str(data["route_path"]).strip()
        if not route.startswith("/payer/"):
            raise HTTPException(status_code=422, detail="route_path must start with /payer/")
        row.route_path = route
    if "requires_catalog" in data:
        row.requires_catalog = bool(data["requires_catalog"])
    if "sort_order" in data and data["sort_order"] is not None:
        row.sort_order = int(data["sort_order"])
    if "status" in data and data["status"]:
        status = str(data["status"]).upper()
        if status not in ("ACTIVE", "DISABLED"):
            raise HTTPException(status_code=422, detail="Invalid status")
        row.status = status
    write_audit(
        db,
        actor_user_id=actor_user_id,
        tenant_id=None,
        entity_type="payment_product",
        entity_id=row.payment_product_id,
        action="UPDATE",
        before=before,
        after=product_to_dict(row),
    )
    db.commit()
    db.refresh(row)
    return row
