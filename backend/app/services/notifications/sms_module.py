from typing import Optional
from urllib import error, request

from app.core.config import get_settings


def send_sms(to_number: str, body: str) -> Optional[str]:
    settings = get_settings()
    if not to_number:
        return "Missing phone number"
    if not settings.SMS_API_URL:
        return None
    payload = (
        f'{{"to":"{to_number}","message":{repr(body)[:500]}}}'
        .replace("'", '"')
    )
    req = request.Request(
        settings.SMS_API_URL,
        data=payload.encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if settings.SMS_API_KEY:
        req.add_header("Authorization", f"Bearer {settings.SMS_API_KEY}")
    try:
        with request.urlopen(req, timeout=15) as resp:
            if resp.status >= 400:
                return f"SMS provider HTTP {resp.status}"
        return None
    except error.URLError as exc:
        return str(exc.reason if hasattr(exc, "reason") else exc)
