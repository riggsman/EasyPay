from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import DbDep, UserDep, require_permissions
from app.schemas.pagination import PaginatedResponse, paginate_query
from app.models.obligation import Obligation
from app.models.payer import Payer
from app.models.revenue import RevenueType
from app.schemas.common import ObligationCreate, ObligationOut
from app.services.payer import get_payer_by_user

router = APIRouter(prefix="/obligations")


@router.get("", response_model=PaginatedResponse[ObligationOut])
def list_obligations(
    db: DbDep,
    current: UserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    payer_id: Optional[str] = None,
    status: Optional[str] = None,
):
    query = db.query(Obligation)
    if current.user_type == "PAYER":
        payer = get_payer_by_user(db, current.user_id)
        query = query.filter(Obligation.payer_id == payer.payer_id)
    elif current.user_type != "PLATFORM_ADMIN":
        query = query.filter(Obligation.tenant_id == current.tenant_id)
    if payer_id:
        query = query.filter(Obligation.payer_id == payer_id)
    if status:
        query = query.filter(Obligation.status == status)
    query = query.order_by(Obligation.created_at.desc())
    items, total, total_pages = paginate_query(query, page, page_size)
    return PaginatedResponse(
        items=[ObligationOut.model_validate(i) for i in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.post("", response_model=ObligationOut)
def create_obligation(body: ObligationCreate, db: DbDep, current = Depends(require_permissions("obligations:write"))):
    payer = db.get(Payer, body.payer_id)
    if not payer:
        raise HTTPException(status_code=404, detail="Payer not found")
    if current.user_type != "PLATFORM_ADMIN" and payer.tenant_id != current.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant isolation violation")
    revenue = db.get(RevenueType, body.revenue_type_id)
    if not revenue:
        raise HTTPException(status_code=404, detail="Revenue type not found")
    if not payer.current_geographic_unit_id or not payer.tenant_id:
        raise HTTPException(status_code=422, detail="Payer has no operating zone")

    obl = Obligation(
        payer_id=payer.payer_id,
        tenant_id=payer.tenant_id,
        geographic_unit_id=payer.current_geographic_unit_id,
        revenue_type_id=body.revenue_type_id,
        financial_period_id=body.financial_period_id,
        description=body.description or revenue.name,
        amount=body.amount,
        balance=body.amount,
        currency=revenue.currency,
        due_date=body.due_date,
        status="DUE",
    )
    db.add(obl)
    db.commit()
    db.refresh(obl)
    return obl


@router.get("/{obligation_id}", response_model=ObligationOut)
def get_obligation(obligation_id: str, db: DbDep, current: UserDep):
    obl = db.get(Obligation, obligation_id)
    if not obl:
        raise HTTPException(status_code=404, detail="Not found")
    if current.user_type == "PAYER":
        payer = get_payer_by_user(db, current.user_id)
        if obl.payer_id != payer.payer_id:
            raise HTTPException(status_code=403, detail="Forbidden")
    elif current.user_type != "PLATFORM_ADMIN" and obl.tenant_id != current.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant isolation violation")
    return obl
