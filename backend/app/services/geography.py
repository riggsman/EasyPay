from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.geography import GeographicUnit, TenantGeographicUnit
from app.models.tenant import Tenant


VALID_UNIT_TYPES = {
    "COUNTRY",
    "REGION",
    "DIVISION",
    "TOWN",
    "MUNICIPALITY",
    "COUNCIL",
    "ZONE",
    "OTHER",
}


def get_unit(db: Session, unit_id: str) -> GeographicUnit:
    unit = db.get(GeographicUnit, unit_id)
    if not unit or unit.status != "ACTIVE":
        raise HTTPException(status_code=404, detail="Geographic unit not found")
    return unit


def validate_parent_child(db: Session, parent_id: Optional[str], unit_type: str) -> None:
    if unit_type not in VALID_UNIT_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid unit_type: {unit_type}")
    if parent_id:
        parent = get_unit(db, parent_id)
        if parent.status != "ACTIVE":
            raise HTTPException(status_code=422, detail="Parent geographic unit is inactive")


def validate_hierarchy_path(db: Session, unit_id: str) -> List[GeographicUnit]:
    """Walk to root ensuring all ancestors are ACTIVE."""
    path: List[GeographicUnit] = []
    current = get_unit(db, unit_id)
    seen = set()
    while current:
        if current.geographic_unit_id in seen:
            raise HTTPException(status_code=422, detail="Circular geography hierarchy")
        seen.add(current.geographic_unit_id)
        path.append(current)
        if not current.parent_id:
            break
        current = get_unit(db, current.parent_id)
    return list(reversed(path))


def resolve_tenant_for_geographic_unit(db: Session, geographic_unit_id: str) -> Tenant:
    mapping = (
        db.query(TenantGeographicUnit)
        .filter(
            TenantGeographicUnit.geographic_unit_id == geographic_unit_id,
            TenantGeographicUnit.status == "ACTIVE",
        )
        .order_by(TenantGeographicUnit.is_primary.desc())
        .first()
    )
    if not mapping:
        raise HTTPException(
            status_code=422,
            detail="Selected council/zone is not linked to an active tenant",
            headers={"X-Error-Code": "ZONE_NO_TENANT"},
        )
    tenant = db.get(Tenant, mapping.tenant_id)
    if not tenant or tenant.status != "ACTIVE":
        raise HTTPException(status_code=422, detail="Tenant for selected zone is inactive")
    return tenant


def list_children(db: Session, parent_id: Optional[str] = None, unit_type: Optional[str] = None) -> List[GeographicUnit]:
    q = db.query(GeographicUnit).filter(GeographicUnit.status == "ACTIVE")
    if parent_id is None:
        q = q.filter(GeographicUnit.parent_id.is_(None))
    else:
        q = q.filter(GeographicUnit.parent_id == parent_id)
    if unit_type:
        q = q.filter(GeographicUnit.unit_type == unit_type)
    return q.order_by(GeographicUnit.unit_name).all()


def ancestry_labels(db: Session, unit_id: str) -> dict:
    path = validate_hierarchy_path(db, unit_id)
    return {
        "path": [{"id": u.geographic_unit_id, "code": u.unit_code, "name": u.unit_name, "type": u.unit_type} for u in path],
        "leaf": path[-1] if path else None,
    }
