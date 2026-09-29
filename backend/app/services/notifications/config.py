from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.config import SystemConfiguration

CONFIG_EMAIL = "notifications.email.enabled"
CONFIG_SMS = "notifications.sms.enabled"
CONFIG_WHATSAPP = "notifications.whatsapp.enabled"


def _config_bool(db: Session, tenant_id: Optional[str], key: str) -> Optional[bool]:
    row = (
        db.query(SystemConfiguration)
        .filter(SystemConfiguration.config_key == key, SystemConfiguration.tenant_id == tenant_id)
        .first()
    )
    if not row:
        return None
    return row.config_value.strip().lower() in ("1", "true", "yes", "on")


def channel_enabled(db: Session, tenant_id: Optional[str], channel: str) -> bool:
    settings = get_settings()
    if channel == "EMAIL":
        if not settings.NOTIFICATIONS_EMAIL_ENABLED:
            return False
        val = _config_bool(db, tenant_id, CONFIG_EMAIL)
        if val is None:
            val = _config_bool(db, None, CONFIG_EMAIL)
        return True if val is None else val
    if channel == "SMS":
        if not settings.NOTIFICATIONS_SMS_ENABLED:
            return False
        val = _config_bool(db, tenant_id, CONFIG_SMS)
        if val is None:
            val = _config_bool(db, None, CONFIG_SMS)
        return False if val is None else val
    if channel == "WHATSAPP":
        if not settings.NOTIFICATIONS_WHATSAPP_ENABLED:
            return False
        val = _config_bool(db, tenant_id, CONFIG_WHATSAPP)
        if val is None:
            val = _config_bool(db, None, CONFIG_WHATSAPP)
        return True if val is None else val
    return False


def notification_settings_snapshot(db: Session, tenant_id: Optional[str]) -> dict:
    settings = get_settings()
    return {
        "email_enabled": channel_enabled(db, tenant_id, "EMAIL"),
        "sms_enabled": channel_enabled(db, tenant_id, "SMS"),
        "whatsapp_enabled": channel_enabled(db, tenant_id, "WHATSAPP"),
        "sms_master_switch": settings.NOTIFICATIONS_SMS_ENABLED,
        "email_master_switch": settings.NOTIFICATIONS_EMAIL_ENABLED,
        "whatsapp_master_switch": settings.NOTIFICATIONS_WHATSAPP_ENABLED,
    }


def upsert_channel_toggle(db: Session, tenant_id: Optional[str], key: str, enabled: bool, description: str) -> None:
    row = (
        db.query(SystemConfiguration)
        .filter(SystemConfiguration.config_key == key, SystemConfiguration.tenant_id == tenant_id)
        .first()
    )
    value = "true" if enabled else "false"
    if row:
        row.config_value = value
        row.description = description
    else:
        db.add(
            SystemConfiguration(
                tenant_id=tenant_id,
                config_key=key,
                config_value=value,
                description=description,
            )
        )
