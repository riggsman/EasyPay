from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import DbDep, UserDep, require_permissions
from app.schemas.pagination import PaginatedResponse, paginate_query
from app.models.settlement import Settlement, SettlementLine
from app.schemas.common import SettlementCreateRequest, SettlementOut
from app.services.settlements import approve_settlement, calculate_settlement, process_settlement

router = APIRouter(prefix="/settlements")


@router.get("", response_model=PaginatedResponse[SettlementOut])
def list_settlements(
    db: DbDep,
    current=Depends(require_permissions("settlements:read")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    status: Optional[str] = None,
):
    query = db.query(Settlement)
    if current.user_type != "PLATFORM_ADMIN":
        query = query.filter(Settlement.tenant_id == current.tenant_id)
    if status:
        query = query.filter(Settlement.status == status)
    query = query.order_by(Settlement.created_at.desc())
    items, total, total_pages = paginate_query(query, page, page_size)
    return PaginatedResponse(
        items=[SettlementOut.model_validate(i) for i in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.post("/calculate", response_model=SettlementOut)
def calc(
    body: SettlementCreateRequest,
    db: DbDep,
    current = Depends(require_permissions("settlements:write")),
    tenant_id: str | None = None,
):
    tid = current.tenant_id
    if current.user_type == "PLATFORM_ADMIN":
        tid = tenant_id or tid
    if not tid:
        raise HTTPException(status_code=422, detail="tenant context required")
    return calculate_settlement(db, tid, body.period_start, body.period_end)


@router.post("/{settlement_id}/approve", response_model=SettlementOut)
def approve(settlement_id: str, db: DbDep, current = Depends(require_permissions("settlements:approve"))):
    s = db.get(Settlement, settlement_id)
    if not s:
        raise HTTPException(status_code=404, detail="Not found")
    if current.user_type != "PLATFORM_ADMIN" and s.tenant_id != current.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant isolation")
    return approve_settlement(db, settlement_id, current.user_id)


@router.post("/{settlement_id}/process", response_model=SettlementOut)
def process(settlement_id: str, db: DbDep, current = Depends(require_permissions("settlements:write"))):
    return process_settlement(db, settlement_id)


@router.get("/{settlement_id}/lines")
def lines(settlement_id: str, db: DbDep, current = Depends(require_permissions("settlements:read"))):
    return db.query(SettlementLine).filter(SettlementLine.settlement_id == settlement_id).all()
