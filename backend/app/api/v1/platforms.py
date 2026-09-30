from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.deps import DbDep, require_permissions
from app.models.platform import Platform
from app.schemas.common import PlatformCreate, PlatformOut
from app.services.branding import ensure_default_platform_logo, save_uploaded_logo

router = APIRouter(prefix="/platforms")


@router.get("", response_model=List[PlatformOut])
def list_platforms(db: DbDep, current=Depends(require_permissions("platforms:read"))):
    ensure_default_platform_logo(db)
    return db.query(Platform).all()


@router.post("", response_model=PlatformOut)
def create_platform(body: PlatformCreate, db: DbDep, current=Depends(require_permissions("platforms:write"))):
    if db.query(Platform).filter(Platform.platform_code == body.platform_code).first():
        raise HTTPException(status_code=422, detail="platform_code already exists")
    platform = Platform(**body.model_dump())
    db.add(platform)
    db.commit()
    db.refresh(platform)
    return platform


@router.get("/{platform_id}", response_model=PlatformOut)
def get_platform(platform_id: str, db: DbDep, current=Depends(require_permissions("platforms:read"))):
    platform = db.get(Platform, platform_id)
    if not platform:
        raise HTTPException(status_code=404, detail="Not found")
    return platform


@router.post("/{platform_id}/logo", response_model=PlatformOut)
async def upload_platform_logo(
    platform_id: str,
    db: DbDep,
    current=Depends(require_permissions("platforms:write")),
    file: UploadFile = File(...),
):
    platform = db.get(Platform, platform_id)
    if not platform:
        raise HTTPException(status_code=404, detail="Not found")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Empty file")
    if len(data) > 2_000_000:
        raise HTTPException(status_code=422, detail="Logo must be under 2MB")
    try:
        platform.logo_path = save_uploaded_logo(
            owner="platform",
            owner_id=platform.platform_id,
            filename=file.filename or "logo.png",
            data=data,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Invalid image: {exc}") from exc
    db.commit()
    db.refresh(platform)
    return platform
