from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import DbDep, UserDep, require_permissions
from app.db.base import utcnow
from app.models.geography import TenantGeographicUnit
from app.models.tenant import Tenant
from app.schemas.common import TenantCreate, TenantGeoMapCreate, TenantOut
from app.services.geography import get_unit

router = APIRouter(prefix="/tenants")


@router.get("", response_model=List[TenantOut])
def list_tenants(db: DbDep, current = Depends(require_permissions("tenants:read"))):
    if current.user_type == "PLATFORM_ADMIN":
        return db.query(Tenant).all()
    if current.tenant_id:
        t = db.get(Tenant, current.tenant_id)
        return [t] if t else []
    return []


@router.post("", response_model=TenantOut)
def create_tenant(body: TenantCreate, db: DbDep, current = Depends(require_permissions("tenants:write"))):
    if db.query(Tenant).filter(Tenant.tenant_code == body.tenant_code).first():
        raise HTTPException(status_code=422, detail="tenant_code already exists")
    data = body.model_dump()
    geo_id = data.pop("geographic_unit_id", None)
    tenant = Tenant(**data)
    db.add(tenant)
    db.flush()
    if geo_id:
        get_unit(db, geo_id)
        db.add(
            TenantGeographicUnit(
                tenant_id=tenant.tenant_id,
                geographic_unit_id=geo_id,
                relationship_type="PRIMARY_COUNCIL",
                is_primary=True,
                effective_from=utcnow(),
            )
        )
    db.commit()
    db.refresh(tenant)
    return tenant


@router.get("/{tenant_id}", response_model=TenantOut)
def get_tenant(tenant_id: str, db: DbDep, current = Depends(require_permissions("tenants:read"))):
    if current.user_type != "PLATFORM_ADMIN" and current.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant isolation violation")
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Not found")
    return tenant


@router.post("/map-geography")
def map_geography(body: TenantGeoMapCreate, db: DbDep, current = Depends(require_permissions("tenants:write"))):
    get_unit(db, body.geographic_unit_id)
    if not db.get(Tenant, body.tenant_id):
        raise HTTPException(status_code=404, detail="Tenant not found")
    mapping = TenantGeographicUnit(**body.model_dump(), effective_from=utcnow())
    db.add(mapping)
    db.commit()
    return {"message": "Mapped", "id": mapping.tenant_geographic_unit_id}
