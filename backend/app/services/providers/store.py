"""Load/save encrypted provider configurations."""
from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.encryption import decrypt_json, encrypt_json, mask_secret
from app.models.provider import ProviderConfiguration

PROVIDER_CAMPAY = "CAMPAY"
PROVIDER_EMAIL = "EMAIL"
PROVIDER_WHATSAPP = "WHATSAPP"
PROVIDER_SMS = "SMS"

SENSITIVE_KEYS = {
    "username",
    "password",
    "api_key",
    "api_secret",
    "app_key",
    "app_secret",
    "smtp_password",
    "access_token",
    "webhook_secret",
}


def get_provider_row(db: Session, provider_code: str) -> Optional[ProviderConfiguration]:
    return db.query(ProviderConfiguration).filter(ProviderConfiguration.provider_code == provider_code).first()


def get_provider_secrets(db: Session, provider_code: str) -> dict[str, Any]:
    row = get_provider_row(db, provider_code)
    if not row or not row.encrypted_payload:
        return {}
    return decrypt_json(row.encrypted_payload)


def upsert_provider_config(
    db: Session,
    *,
    provider_code: str,
    display_name: str,
    enabled: bool,
    secrets: dict[str, Any],
    public_meta: Optional[dict[str, Any]] = None,
    updated_by: Optional[str] = None,
    merge_secrets: bool = True,
) -> ProviderConfiguration:
    row = get_provider_row(db, provider_code)
    existing = get_provider_secrets(db, provider_code) if row and merge_secrets else {}
    merged = {**existing}
    for key, value in secrets.items():
        if value is None:
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        # Skip unchanged masked placeholders
        if isinstance(value, str) and set(value) <= {"*"} and key in existing:
            continue
        merged[key] = value

    payload = encrypt_json(merged)
    meta_json = json.dumps(public_meta or {})
    if row:
        row.display_name = display_name
        row.enabled = enabled
        row.encrypted_payload = payload
        row.public_meta = meta_json
        row.updated_by = updated_by
    else:
        row = ProviderConfiguration(
            provider_code=provider_code,
            display_name=display_name,
            enabled=enabled,
            encrypted_payload=payload,
            public_meta=meta_json,
            updated_by=updated_by,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def public_provider_view(db: Session, provider_code: str) -> dict[str, Any]:
    row = get_provider_row(db, provider_code)
    secrets = get_provider_secrets(db, provider_code) if row else {}
    public_meta = {}
    if row and row.public_meta:
        try:
            public_meta = json.loads(row.public_meta)
        except json.JSONDecodeError:
            public_meta = {}
    masked = {}
    for key, value in secrets.items():
        if key in SENSITIVE_KEYS or key.endswith("_password") or key.endswith("_secret") or key.endswith("_key"):
            masked[key] = mask_secret(str(value)) if value else ""
            masked[f"{key}_configured"] = bool(value)
        else:
            masked[key] = value
    return {
        "provider_code": provider_code,
        "display_name": row.display_name if row else provider_code,
        "enabled": bool(row.enabled) if row else False,
        "configured": bool(row and row.encrypted_payload),
        "public_meta": public_meta,
        "settings": masked,
        "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
    }
