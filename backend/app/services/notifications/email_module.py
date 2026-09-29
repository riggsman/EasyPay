import smtplib
from email.message import EmailMessage
from typing import Optional

from app.core.config import get_settings


def send_email(to_address: str, subject: str, body: str) -> Optional[str]:
    settings = get_settings()
    if not to_address:
        return "Missing recipient email"
    if not settings.SMTP_HOST:
        return None
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER or "noreply@easypay.local"
    msg["To"] = to_address
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
        return None
    except Exception as exc:  # noqa: BLE001 — log delivery failure, do not break domain flow
        return str(exc)
