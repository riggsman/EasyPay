from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import DbDep, UserDep, require_permissions
from app.models.geography import GeographicUnit
from app.schemas.common import GeographicUnitCreate, GeographicUnitOut
from app.services.geography import ancestry_labels, list_children, validate_parent_child

router = APIRouter(prefix="/geography")


@router.get("/units", response_model=List[GeographicUnitOut])
def list_units(
    db: DbDep,
    parent_id: Optional[str] = None,
    unit_type: Optional[str] = None,
    roots: bool = Query(False),
):
    if roots:
        return list_children(db, None, unit_type)
    if parent_id is not None:
        return list_children(db, parent_id, unit_type)
    return db.query(GeographicUnit).filter(GeographicUnit.status == "ACTIVE").order_by(GeographicUnit.unit_name).all()


@router.get("/children", response_model=List[GeographicUnitOut])
def children(db: DbDep, parent_id: Optional[str] = None, unit_type: Optional[str] = None):
    return list_children(db, parent_id, unit_type)


@router.get("/units/{unit_id}/ancestry")
def unit_ancestry(unit_id: str, db: DbDep):
    return ancestry_labels(db, unit_id)


@router.post("/units", response_model=GeographicUnitOut)
def create_unit(body: GeographicUnitCreate, db: DbDep, current = Depends(require_permissions("geography:write"))):
    validate_parent_child(db, body.parent_id, body.unit_type)
    if db.query(GeographicUnit).filter(GeographicUnit.unit_code == body.unit_code).first():
        raise HTTPException(status_code=422, detail="unit_code already exists")
    unit = GeographicUnit(**body.model_dump())
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit
