"""Encrypted provider configuration APIs — Campay, Email, WhatsApp (system/super admin only)."""
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.deps import DbDep, SystemAdminDep
from app.services.providers import store as provider_store
from app.services.audit import write_audit

router = APIRouter(prefix="/providers", tags=["providers"])


class ProviderUpsertIn(BaseModel):
    enabled: bool = False
    display_name: Optional[str] = None
    settings: dict[str, Any] = Field(default_factory=dict)
    public_meta: dict[str, Any] = Field(default_factory=dict)


@router.get("")
def list_providers(db: DbDep, current: SystemAdminDep):
    defaults = {
        provider_store.PROVIDER_CAMPAY: "Campay (Mobile Money)",
        provider_store.PROVIDER_EMAIL: "Email (SMTP)",
        provider_store.PROVIDER_WHATSAPP: "WhatsApp",
        provider_store.PROVIDER_SMS: "SMS",
    }
    out = []
    for code, default_name in defaults.items():
        view = provider_store.public_provider_view(db, code)
        if not view.get("configured"):
            view["display_name"] = default_name
        out.append(view)
    return out


@router.get("/{provider_code}")
def get_provider(provider_code: str, db: DbDep, current: SystemAdminDep):
    return provider_store.public_provider_view(db, provider_code.upper())


@router.put("/campay")
def upsert_campay(body: ProviderUpsertIn, db: DbDep, current: SystemAdminDep):
    row = provider_store.upsert_provider_config(
        db,
        provider_code=provider_store.PROVIDER_CAMPAY,
        display_name=body.display_name or "Campay",
        enabled=body.enabled,
        secrets=body.settings,
        public_meta={
            **body.public_meta,
            "base_url_hint": body.settings.get("base_url") or body.public_meta.get("base_url_hint"),
        },
        updated_by=current.user_id,
    )
    write_audit(
        db,
        actor_user_id=current.user_id,
        tenant_id=None,
        entity_type="provider_configuration",
        entity_id=row.provider_config_id,
        action="UPSERT_CAMPAY",
        after={"enabled": body.enabled},
    )
    db.commit()
    return provider_store.public_provider_view(db, provider_store.PROVIDER_CAMPAY)


@router.put("/email")
def upsert_email(body: ProviderUpsertIn, db: DbDep, current: SystemAdminDep):
    row = provider_store.upsert_provider_config(
        db,
        provider_code=provider_store.PROVIDER_EMAIL,
        display_name=body.display_name or "Email SMTP",
        enabled=body.enabled,
        secrets=body.settings,
        public_meta=body.public_meta,
        updated_by=current.user_id,
    )
    write_audit(
        db,
        actor_user_id=current.user_id,
        tenant_id=None,
        entity_type="provider_configuration",
        entity_id=row.provider_config_id,
        action="UPSERT_EMAIL",
        after={"enabled": body.enabled, "smtp_host": body.settings.get("smtp_host")},
    )
    db.commit()
    return provider_store.public_provider_view(db, provider_store.PROVIDER_EMAIL)


@router.put("/whatsapp")
def upsert_whatsapp(body: ProviderUpsertIn, db: DbDep, current: SystemAdminDep):
    row = provider_store.upsert_provider_config(
        db,
        provider_code=provider_store.PROVIDER_WHATSAPP,
        display_name=body.display_name or "WhatsApp",
        enabled=body.enabled,
        secrets=body.settings,
        public_meta=body.public_meta,
        updated_by=current.user_id,
    )
    write_audit(
        db,
        actor_user_id=current.user_id,
        tenant_id=None,
        entity_type="provider_configuration",
        entity_id=row.provider_config_id,
        action="UPSERT_WHATSAPP",
        after={"enabled": body.enabled},
    )
    db.commit()
    return provider_store.public_provider_view(db, provider_store.PROVIDER_WHATSAPP)


@router.put("/sms")
def upsert_sms(body: ProviderUpsertIn, db: DbDep, current: SystemAdminDep):
    row = provider_store.upsert_provider_config(
        db,
        provider_code=provider_store.PROVIDER_SMS,
        display_name=body.display_name or "SMS",
        enabled=body.enabled,
        secrets=body.settings,
        public_meta=body.public_meta,
        updated_by=current.user_id,
    )
    write_audit(
        db,
        actor_user_id=current.user_id,
        tenant_id=None,
        entity_type="provider_configuration",
        entity_id=row.provider_config_id,
        action="UPSERT_SMS",
        after={"enabled": body.enabled},
    )
    db.commit()
    return provider_store.public_provider_view(db, provider_store.PROVIDER_SMS)


@router.post("/campay/test-token")
def test_campay_token(db: DbDep, current: SystemAdminDep):
    from app.services.providers.campay import CampayClient

    client = CampayClient(db)
    try:
        token = client.get_token()
        return {"ok": True, "mock": client.mock, "token_preview": f"{token[:8]}…" if token else None}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc
