"""Platform-configurable client-side response cache TTL."""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.config import SystemConfiguration

CONFIG_CLIENT_CACHE_TTL = "client.cache_ttl_seconds"
DEFAULT_TTL_SECONDS = 15 * 60  # 15 minutes
MIN_TTL_SECONDS = 15 * 60
MAX_TTL_SECONDS = 24 * 60 * 60  # 24 hours


def _config_value(db: Session, key: str) -> Optional[str]:
    row = (
        db.query(SystemConfiguration)
        .filter(SystemConfiguration.config_key == key, SystemConfiguration.tenant_id.is_(None))
        .first()
    )
    return row.config_value if row else None


def get_client_cache_ttl_seconds(db: Session) -> int:
    raw = _config_value(db, CONFIG_CLIENT_CACHE_TTL)
    try:
        ttl = int(raw) if raw is not None else DEFAULT_TTL_SECONDS
    except (TypeError, ValueError):
        ttl = DEFAULT_TTL_SECONDS
    if ttl < MIN_TTL_SECONDS:
        ttl = MIN_TTL_SECONDS
    if ttl > MAX_TTL_SECONDS:
        ttl = MAX_TTL_SECONDS
    return ttl


def ensure_default_client_cache_settings(db: Session) -> dict:
    ttl = get_client_cache_ttl_seconds(db)
    if _config_value(db, CONFIG_CLIENT_CACHE_TTL) is None:
        db.add(
            SystemConfiguration(
                tenant_id=None,
                config_key=CONFIG_CLIENT_CACHE_TTL,
                config_value=str(DEFAULT_TTL_SECONDS),
                description="Client GET response cache TTL in seconds (platform-wide)",
            )
        )
        db.commit()
        ttl = DEFAULT_TTL_SECONDS
    return {
        "ttl_seconds": ttl,
        "ttl_minutes": ttl // 60,
        "default_ttl_seconds": DEFAULT_TTL_SECONDS,
        "min_ttl_seconds": MIN_TTL_SECONDS,
        "max_ttl_seconds": MAX_TTL_SECONDS,
    }


def update_client_cache_ttl(db: Session, *, ttl_seconds: Optional[int] = None, ttl_minutes: Optional[int] = None) -> dict:
    if ttl_seconds is None and ttl_minutes is None:
        raise HTTPException(status_code=400, detail="Provide ttl_seconds or ttl_minutes")
    if ttl_seconds is None:
        ttl_seconds = int(ttl_minutes) * 60
    ttl_seconds = int(ttl_seconds)
    if ttl_seconds < MIN_TTL_SECONDS:
        raise HTTPException(
            status_code=400,
            detail=f"Cache time must be at least {MIN_TTL_SECONDS // 60} minutes",
        )
    if ttl_seconds > MAX_TTL_SECONDS:
        raise HTTPException(
            status_code=400,
            detail=f"Cache time cannot exceed {MAX_TTL_SECONDS // 3600} hours",
        )
    row = (
        db.query(SystemConfiguration)
        .filter(SystemConfiguration.config_key == CONFIG_CLIENT_CACHE_TTL, SystemConfiguration.tenant_id.is_(None))
        .first()
    )
    if row:
        row.config_value = str(ttl_seconds)
        row.description = "Client GET response cache TTL in seconds (platform-wide)"
    else:
        db.add(
            SystemConfiguration(
                tenant_id=None,
                config_key=CONFIG_CLIENT_CACHE_TTL,
                config_value=str(ttl_seconds),
                description="Client GET response cache TTL in seconds (platform-wide)",
            )
        )
    db.commit()
    return ensure_default_client_cache_settings(db)
