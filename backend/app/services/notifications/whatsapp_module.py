from typing import Optional
from urllib import error, request

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.providers import store as provider_store


def send_whatsapp(to_number: str, body: str, db: Optional[Session] = None) -> Optional[str]:
    settings = get_settings()
    cfg = provider_store.get_provider_secrets(db, provider_store.PROVIDER_WHATSAPP) if db else {}
    if not to_number:
        return "Missing WhatsApp number"
    if str(cfg.get("mock", "")).lower() in ("1", "true", "yes", "on"):
        return None
    api_url = cfg.get("api_url") or settings.WHATSAPP_API_URL
    api_key = cfg.get("api_key") or settings.WHATSAPP_API_KEY
    if not api_url:
        return None
    payload = (
        f'{{"to":"{to_number}","type":"text","text":{repr(body)[:500]}}}'
        .replace("'", '"')
    )
    req = request.Request(
        api_url,
        data=payload.encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    try:
        with request.urlopen(req, timeout=15) as resp:
            if resp.status >= 400:
                return f"WhatsApp provider HTTP {resp.status}"
        return None
    except error.URLError as exc:
        return str(exc.reason if hasattr(exc, "reason") else exc)
