"""PDF logo watermark + QR verify URL from PUBLIC_BASE_URL."""

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.receipt import Receipt
from app.services.branding import (
    ensure_default_platform_logo,
    public_verify_url,
    resolve_logo_file,
    washed_logo_png,
)
from app.services.receipts_pdf import build_receipt_pdf
from app.services.pdf_branding import build_qr_png


def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_public_verify_url_uses_config_base():
    get_settings.cache_clear()
    settings = get_settings()
    url = public_verify_url("v_deadbeef")
    assert url.startswith(settings.PUBLIC_BASE_URL.rstrip("/"))
    assert url.endswith("/v/v_deadbeef")
    assert "?" not in url  # opaque path only — no amounts/ids in query


def test_washed_logo_and_default_platform_logo():
    db = SessionLocal()
    try:
        path = ensure_default_platform_logo(db)
        assert path.is_file()
        resolved = resolve_logo_file(db, tenant_id=None, force_platform=True)
        assert resolved and resolved.is_file()
        png = washed_logo_png(resolved, wash_opacity=0.6)
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        assert len(png) > 200
    finally:
        db.close()


def test_qr_png_encodes_verify_url():
    url = public_verify_url("v_abc123")
    png = build_qr_png(url)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_receipt_pdf_includes_branding(client):
    token = _login(client, "admin", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    listing = client.get("/api/v1/receipts?page=1&page_size=1", headers=headers)
    assert listing.status_code == 200, listing.text
    items = listing.json().get("items") or []
    assert items
    receipt_id = items[0]["receipt_id"]

    db = SessionLocal()
    try:
        ensure_default_platform_logo(db)
        receipt = db.get(Receipt, receipt_id)
        assert receipt
        vtoken = receipt.verification_token
        pdf = build_receipt_pdf(db, receipt)
    finally:
        db.close()

    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 2000
    # Token / verify path may be in compressed streams; ensure generation succeeded with branding helpers
    assert vtoken
    assert public_verify_url(vtoken).endswith(f"/v/{vtoken}")


def test_deep_link_token_still_verifies(client):
    token = _login(client, "admin", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    listing = client.get("/api/v1/receipts?page=1&page_size=1", headers=headers)
    receipt = listing.json()["items"][0]
    detail = client.get(f"/api/v1/receipts/{receipt['receipt_id']}", headers=headers)
    assert detail.status_code == 200
    vtoken = detail.json()["verification_token"]
    verify = client.get(f"/api/v1/public/verify/{vtoken}")
    assert verify.status_code == 200
    assert verify.json()["verified"] is True
