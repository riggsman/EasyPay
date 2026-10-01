"""Utility service catalog + bill-pay (meter XOR bill) flows."""

import subprocess
import sys
from pathlib import Path

from app.db.session import SessionLocal
from app.models.utility import UtilityService
from app.services.utilities import ensure_sample_utility_services


def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _ensure():
    root = Path(__file__).resolve().parents[2]
    subprocess.run([sys.executable, str(root / "scripts" / "migrate_utilities.py")], check=True, cwd=str(root))
    db = SessionLocal()
    try:
        ensure_sample_utility_services(db)
    finally:
        db.close()


def test_store_lists_only_active_services(client):
    _ensure()
    token = _login(client, "abctrading", "payer123")
    headers = {"Authorization": f"Bearer {token}"}
    store = client.get("/api/v1/utility-services/store", headers=headers)
    assert store.status_code == 200, store.text
    codes = {s["code"] for s in store.json()}
    assert "ENEO" in codes
    assert "CAMWATER" in codes
    assert "DEMO-DISABLED" not in codes


def test_admin_can_disable_and_hide_from_store(client):
    _ensure()
    admin = _login(client, "admin", "admin123")
    ah = {"Authorization": f"Bearer {admin}"}
    listing = client.get("/api/v1/utility-services", headers=ah)
    assert listing.status_code == 200, listing.text
    eneo = next(s for s in listing.json() if s["code"] == "ENEO")
    patched = client.patch(
        f"/api/v1/utility-services/{eneo['utility_service_id']}",
        headers=ah,
        json={"status": "DISABLED"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["status"] == "DISABLED"

    payer = _login(client, "abctrading", "payer123")
    store = client.get("/api/v1/utility-services/store", headers={"Authorization": f"Bearer {payer}"})
    codes = {s["code"] for s in store.json()}
    assert "ENEO" not in codes

    # restore for other tests
    client.patch(
        f"/api/v1/utility-services/{eneo['utility_service_id']}",
        headers=ah,
        json={"status": "ACTIVE"},
    )


def test_utility_pay_rejects_both_meter_and_bill(client):
    _ensure()
    token = _login(client, "abctrading", "payer123")
    headers = {"Authorization": f"Bearer {token}"}
    store = client.get("/api/v1/utility-services/store", headers=headers).json()
    svc = next(s for s in store if s["code"] == "ENEO")
    bad = client.post(
        "/api/v1/utility-payments/initiate",
        headers=headers,
        json={
            "utility_service_id": svc["utility_service_id"],
            "amount": 10000,
            "meter_number": "M-1",
            "bill_number": "B-1",
            "phone_number": "670000001",
            "idempotency_key": "utl-both-refs-test-001",
        },
    )
    assert bad.status_code == 422


def test_utility_pay_success_with_meter_records_history_and_receipt(client):
    _ensure()
    token = _login(client, "abctrading", "payer123")
    headers = {"Authorization": f"Bearer {token}"}
    store = client.get("/api/v1/utility-services/store", headers=headers).json()
    svc = next(s for s in store if s["code"] == "CAMWATER")
    quote = client.post(
        "/api/v1/utility-payments/quote",
        headers=headers,
        json={"utility_service_id": svc["utility_service_id"], "amount": 8500},
    )
    assert quote.status_code == 200, quote.text
    assert float(quote.json()["service_fee"]) == 300.0

    pay = client.post(
        "/api/v1/utility-payments/initiate",
        headers=headers,
        json={
            "utility_service_id": svc["utility_service_id"],
            "amount": 8500,
            "meter_number": "CW-METER-7788",
            "phone_number": "670000001",
            "idempotency_key": "utl-success-camwater-001",
        },
    )
    assert pay.status_code == 200, pay.text
    body = pay.json()
    assert body["ok"] is True
    assert body["status"] == "SETTLED"
    assert body["product_type"] == "UTILITY"
    assert body["receipt_id"]
    assert body["utility"]["reference_type"] == "METER"
    assert body["utility"]["meter_number"] == "CW-METER-7788"

    detail = client.get(f"/api/v1/payments/{body['transaction_id']}", headers=headers)
    assert detail.status_code == 200
    d = detail.json()
    assert d["product_type"] == "UTILITY"
    assert d["utility"]["service_code"] == "CAMWATER"
    assert d["receipt_pdf_url"]

    pdf = client.get(d["receipt_pdf_url"], headers=headers)
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"


def test_utility_pay_failure_still_recorded(client):
    _ensure()
    token = _login(client, "abctrading", "payer123")
    headers = {"Authorization": f"Bearer {token}"}
    store = client.get("/api/v1/utility-services/store", headers=headers).json()
    svc = next(s for s in store if s["code"] == "ENEO")
    pay = client.post(
        "/api/v1/utility-payments/initiate",
        headers=headers,
        json={
            "utility_service_id": svc["utility_service_id"],
            "amount": 12000,
            "bill_number": "ENEO-BILL-99",
            "phone_number": "670000001",
            "idempotency_key": f"utl-fail-eneo-{__import__('uuid').uuid4().hex[:10]}",
            "simulate_failure": True,
        },
    )
    assert pay.status_code == 200, pay.text
    body = pay.json()
    assert body["ok"] is False
    assert body["status"] == "FAILED"
    assert body["failure_reason"]
    assert body["receipt_id"] is None

    hist = client.get("/api/v1/payments?page=1&page_size=50", headers=headers)
    assert hist.status_code == 200
    refs = {i["transaction_reference"] for i in hist.json()["items"]}
    assert body["transaction_reference"] in refs


def test_admin_create_service_appears_in_store(client):
    _ensure()
    admin = _login(client, "admin", "admin123")
    ah = {"Authorization": f"Bearer {admin}"}
    code = f"GAS{__import__('uuid').uuid4().hex[:6].upper()}"
    created = client.post(
        "/api/v1/utility-services",
        headers=ah,
        json={
            "code": code,
            "name": "Test Gas Bill",
            "description": "Sample gas utility",
            "category": "OTHER",
            "fee_type": "FLAT",
            "fee_value": 250,
            "accept_meter_number": False,
            "accept_bill_number": True,
            "status": "ACTIVE",
            "sort_order": 30,
        },
    )
    assert created.status_code == 200, created.text
    payer = _login(client, "abctrading", "payer123")
    store = client.get("/api/v1/utility-services/store", headers={"Authorization": f"Bearer {payer}"})
    codes = {s["code"] for s in store.json()}
    assert code in codes

    # cleanup disable
    client.patch(
        f"/api/v1/utility-services/{created.json()['utility_service_id']}",
        headers=ah,
        json={"status": "DISABLED"},
    )
