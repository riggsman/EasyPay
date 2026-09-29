from typing import List, Optional

from fastapi import APIRouter, HTTPException

from app.core.deps import DbDep, UserDep, require_permissions
from app.models.platform import Platform
from app.schemas.common import PlatformCreate, PlatformOut
from fastapi import Depends

router = APIRouter(prefix="/platforms")


@router.get("", response_model=List[PlatformOut])
def list_platforms(db: DbDep, current = Depends(require_permissions("platforms:read"))):
    return db.query(Platform).all()


@router.post("", response_model=PlatformOut)
def create_platform(body: PlatformCreate, db: DbDep, current = Depends(require_permissions("platforms:write"))):
    if db.query(Platform).filter(Platform.platform_code == body.platform_code).first():
        raise HTTPException(status_code=422, detail="platform_code already exists")
    platform = Platform(**body.model_dump())
    db.add(platform)
    db.commit()
    db.refresh(platform)
    return platform


@router.get("/{platform_id}", response_model=PlatformOut)
def get_platform(platform_id: str, db: DbDep, current = Depends(require_permissions("platforms:read"))):
    platform = db.get(Platform, platform_id)
    if not platform:
        raise HTTPException(status_code=404, detail="Not found")
    return platform
