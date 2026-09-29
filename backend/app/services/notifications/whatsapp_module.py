from typing import Optional
from urllib import error, request

from app.core.config import get_settings


def send_whatsapp(to_number: str, body: str) -> Optional[str]:
    settings = get_settings()
    if not to_number:
        return "Missing WhatsApp number"
    if not settings.WHATSAPP_API_URL:
        return None
    payload = (
        f'{{"to":"{to_number}","type":"text","text":{repr(body)[:500]}}}'
        .replace("'", '"')
    )
    req = request.Request(
        settings.WHATSAPP_API_URL,
        data=payload.encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if settings.WHATSAPP_API_KEY:
        req.add_header("Authorization", f"Bearer {settings.WHATSAPP_API_KEY}")
    try:
        with request.urlopen(req, timeout=15) as resp:
            if resp.status >= 400:
                return f"WhatsApp provider HTTP {resp.status}"
        return None
    except error.URLError as exc:
        return str(exc.reason if hasattr(exc, "reason") else exc)
