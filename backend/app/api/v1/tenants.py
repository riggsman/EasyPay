from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.deps import DbDep, require_permissions
from app.db.base import utcnow
from app.models.geography import TenantGeographicUnit
from app.models.tenant import Tenant
from app.schemas.common import TenantCreate, TenantGeoMapCreate, TenantOut
from app.services.branding import absolute_logo_path, save_uploaded_logo
from app.services.geography import get_unit

router = APIRouter(prefix="/tenants")

_MAX_LOGO_BYTES = 2_000_000


def _assert_tenant_access(current, tenant_id: str) -> None:
    if current.user_type not in ("PLATFORM_ADMIN", "SUPER_ADMIN") and current.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant isolation violation")


def _apply_logo_bytes(tenant: Tenant, *, filename: str, data: bytes) -> None:
    if not data:
        raise HTTPException(status_code=422, detail="Empty file")
    if len(data) > _MAX_LOGO_BYTES:
        raise HTTPException(status_code=422, detail="Logo must be under 2MB")
    try:
        tenant.logo_path = save_uploaded_logo(
            owner="tenants",
            owner_id=tenant.tenant_id,
            filename=filename or "logo.png",
            data=data,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Invalid image: {exc}") from exc


def _create_tenant_row(db, body: TenantCreate) -> Tenant:
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
    return tenant


@router.get("", response_model=List[TenantOut])
def list_tenants(db: DbDep, current=Depends(require_permissions("tenants:read"))):
    if current.user_type in ("PLATFORM_ADMIN", "SUPER_ADMIN"):
        return db.query(Tenant).all()
    if current.tenant_id:
        t = db.get(Tenant, current.tenant_id)
        return [t] if t else []
    return []


@router.post("", response_model=TenantOut)
def create_tenant(body: TenantCreate, db: DbDep, current=Depends(require_permissions("tenants:write"))):
    tenant = _create_tenant_row(db, body)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.post("/register", response_model=TenantOut)
async def register_tenant_with_logo(
    db: DbDep,
    current=Depends(require_permissions("tenants:write")),
    tenant_code: str = Form(...),
    organization_name: str = Form(...),
    organization_type: str = Form("COUNCIL"),
    email: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    currency: str = Form("XAF"),
    zone_change_mode: str = Form("IMMEDIATE"),
    geographic_unit_id: Optional[str] = Form(None),
    logo: Optional[UploadFile] = File(None),
):
    """Register a tenant and optionally upload logo/image in the same request."""
    body = TenantCreate(
        tenant_code=tenant_code.strip().upper(),
        organization_name=organization_name.strip(),
        organization_type=(organization_type or "COUNCIL").strip().upper(),
        email=email or None,
        phone_number=phone_number or None,
        currency=(currency or "XAF").strip().upper(),
        zone_change_mode=(zone_change_mode or "IMMEDIATE").strip().upper(),
        geographic_unit_id=geographic_unit_id or None,
    )
    tenant = _create_tenant_row(db, body)
    if logo is not None and logo.filename:
        data = await logo.read()
        if data:
            _apply_logo_bytes(tenant, filename=logo.filename, data=data)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.get("/{tenant_id}", response_model=TenantOut)
def get_tenant(tenant_id: str, db: DbDep, current=Depends(require_permissions("tenants:read"))):
    _assert_tenant_access(current, tenant_id)
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Not found")
    return tenant


@router.post("/map-geography")
def map_geography(body: TenantGeoMapCreate, db: DbDep, current=Depends(require_permissions("tenants:write"))):
    get_unit(db, body.geographic_unit_id)
    if not db.get(Tenant, body.tenant_id):
        raise HTTPException(status_code=404, detail="Tenant not found")
    mapping = TenantGeographicUnit(**body.model_dump(), effective_from=utcnow())
    db.add(mapping)
    db.commit()
    return {"message": "Mapped", "id": mapping.tenant_geographic_unit_id}


@router.get("/{tenant_id}/logo")
def get_tenant_logo(tenant_id: str, db: DbDep, current=Depends(require_permissions("tenants:read"))):
    _assert_tenant_access(current, tenant_id)
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Not found")
    path = absolute_logo_path(tenant.logo_path)
    if not path:
        raise HTTPException(status_code=404, detail="Logo not found")
    return FileResponse(path, media_type="image/png", filename=f"{tenant.tenant_code}-logo.png")


@router.post("/{tenant_id}/logo", response_model=TenantOut)
async def upload_tenant_logo(
    tenant_id: str,
    db: DbDep,
    current=Depends(require_permissions("tenants:write")),
    file: UploadFile = File(...),
):
    _assert_tenant_access(current, tenant_id)
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Not found")
    data = await file.read()
    _apply_logo_bytes(tenant, filename=file.filename or "logo.png", data=data)
    db.commit()
    db.refresh(tenant)
    return tenant
