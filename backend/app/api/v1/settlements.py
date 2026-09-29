from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import DbDep, UserDep, require_permissions
from app.models.settlement import Settlement, SettlementLine
from app.schemas.common import SettlementCreateRequest, SettlementOut
from app.services.settlements import approve_settlement, calculate_settlement, process_settlement

router = APIRouter(prefix="/settlements")


@router.get("", response_model=List[SettlementOut])
def list_settlements(db: DbDep, current = Depends(require_permissions("settlements:read"))):
    q = db.query(Settlement)
    if current.user_type != "PLATFORM_ADMIN":
        q = q.filter(Settlement.tenant_id == current.tenant_id)
    return q.order_by(Settlement.created_at.desc()).all()


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
