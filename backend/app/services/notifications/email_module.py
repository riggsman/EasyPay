import smtplib
from email.message import EmailMessage
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.providers import store as provider_store


def _smtp_settings(db: Optional[Session] = None) -> dict:
    settings = get_settings()
    cfg = provider_store.get_provider_secrets(db, provider_store.PROVIDER_EMAIL) if db else {}
    row = provider_store.get_provider_row(db, provider_store.PROVIDER_EMAIL) if db else None
    enabled = bool(row.enabled) if row else settings.NOTIFICATIONS_EMAIL_ENABLED
    return {
        "enabled": enabled if row else settings.NOTIFICATIONS_EMAIL_ENABLED,
        "host": cfg.get("smtp_host") or settings.SMTP_HOST,
        "port": int(cfg.get("smtp_port") or settings.SMTP_PORT or 587),
        "user": cfg.get("smtp_user") or settings.SMTP_USER,
        "password": cfg.get("smtp_password") or settings.SMTP_PASSWORD,
        "from_addr": cfg.get("smtp_from") or settings.SMTP_FROM or settings.SMTP_USER or "noreply@easypay.local",
        "use_tls": str(cfg.get("smtp_use_tls", settings.SMTP_USE_TLS)).lower() in ("1", "true", "yes", "on"),
    }


def send_email(to_address: str, subject: str, body: str, db: Optional[Session] = None) -> Optional[str]:
    if not to_address:
        return "Missing recipient email"
    cfg = _smtp_settings(db)
    if not cfg["host"]:
        return None
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["from_addr"]
    msg["To"] = to_address
    msg.set_content(body)
    try:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as smtp:
            if cfg["use_tls"]:
                smtp.starttls()
            if cfg["user"] and cfg["password"]:
                smtp.login(cfg["user"], cfg["password"])
            smtp.send_message(msg)
        return None
    except Exception as exc:  # noqa: BLE001
        return str(exc)
