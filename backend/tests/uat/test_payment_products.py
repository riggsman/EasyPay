"""Payment product chooser for council / utility / future types."""

import subprocess
import sys
from pathlib import Path

from app.db.session import SessionLocal
from app.services.payment_products import ensure_default_payment_products


def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _ensure():
    root = Path(__file__).resolve().parents[2]
    subprocess.run([sys.executable, str(root / "scripts" / "migrate_utilities.py")], check=True, cwd=str(root))
    db = SessionLocal()
    try:
        ensure_default_payment_products(db)
    finally:
        db.close()


def test_payer_chooser_includes_council_and_utility(client):
    _ensure()
    token = _login(client, "abctrading", "payer123")
    res = client.get("/api/v1/payment-products/chooser", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    rows = res.json()
    by_code = {r["code"]: r for r in rows}
    assert "COUNCIL" in by_code
    assert by_code["COUNCIL"]["available"] is True
    assert by_code["COUNCIL"]["route_path"] == "/payer/pay/council"
    assert "UTILITY" in by_code
    assert by_code["UTILITY"]["route_path"] == "/payer/pay/utilities"
    assert by_code["UTILITY"]["available"] is True
    assert by_code["UTILITY"]["catalog_count"] >= 1


def test_admin_can_disable_product_from_chooser(client):
    _ensure()
    admin = _login(client, "admin", "admin123")
    ah = {"Authorization": f"Bearer {admin}"}
    listing = client.get("/api/v1/payment-products", headers=ah)
    assert listing.status_code == 200
    util = next(r for r in listing.json() if r["code"] == "UTILITY")
    patched = client.patch(
        f"/api/v1/payment-products/{util['payment_product_id']}",
        headers=ah,
        json={"status": "DISABLED"},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "DISABLED"

    payer = _login(client, "abctrading", "payer123")
    chooser = client.get("/api/v1/payment-products/chooser", headers={"Authorization": f"Bearer {payer}"})
    codes = {r["code"] for r in chooser.json()}
    assert "UTILITY" not in codes
    assert "COUNCIL" in codes

    client.patch(
        f"/api/v1/payment-products/{util['payment_product_id']}",
        headers=ah,
        json={"status": "ACTIVE"},
    )


def test_admin_registers_future_product(client):
    _ensure()
    admin = _login(client, "admin", "admin123")
    ah = {"Authorization": f"Bearer {admin}"}
    code = f"FUT{__import__('uuid').uuid4().hex[:5].upper()}"
    created = client.post(
        "/api/v1/payment-products",
        headers=ah,
        json={
            "code": code,
            "name": "Future school fees",
            "description": "Placeholder product for upcoming school-fee payments",
            "route_path": "/payer/pay/school-fees",
            "status": "ACTIVE",
            "sort_order": 40,
        },
    )
    assert created.status_code == 200, created.text
    payer = _login(client, "abctrading", "payer123")
    chooser = client.get("/api/v1/payment-products/chooser", headers={"Authorization": f"Bearer {payer}"})
    row = next(r for r in chooser.json() if r["code"] == code)
    assert row["route_path"] == "/payer/pay/school-fees"
    assert row["available"] is True

    client.patch(
        f"/api/v1/payment-products/{created.json()['payment_product_id']}",
        headers=ah,
        json={"status": "DISABLED"},
    )
