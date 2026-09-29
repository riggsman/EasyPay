from decimal import Decimal
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _council_ids(client):
    cm = client.get("/api/v1/geography/children").json()[0]
    regions = client.get(f"/api/v1/geography/children?parent_id={cm['geographic_unit_id']}").json()
    divisions = client.get(f"/api/v1/geography/children?parent_id={regions[0]['geographic_unit_id']}").json()
    towns = client.get(f"/api/v1/geography/children?parent_id={divisions[0]['geographic_unit_id']}").json()
    councils = client.get(f"/api/v1/geography/children?parent_id={towns[0]['geographic_unit_id']}").json()
    by_code = {c["unit_code"]: c for c in councils}
    return by_code


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_and_geography(client):
    token = _login(client, "admin", "admin123")
    r = client.get("/api/v1/geography/children", headers={"Authorization": f"Bearer {token}"})
    r = client.get("/api/v1/geography/children")
    assert r.status_code == 200
    assert any(u["unit_code"] == "CM" for u in r.json())


def test_payer_payment_and_history_invariant(client):
    councils = _council_ids(client)
    kumba1 = councils["KUMBA-01"]
    kumba3 = councils["KUMBA-03"]
    suffix = uuid.uuid4().hex[:8]
    username = f"payer_{suffix}"

    reg = client.post(
        "/api/v1/payers/register",
        json={
            "full_name": "Test Payer",
            "business_name": "Test Biz",
            "email": f"{username}@example.com",
            "phone_number": f"670{suffix[:6]}",
            "username": username,
            "password": "payer123",
            "password_confirm": "payer123",
            "payer_type": "BUSINESS",
            "address": "Test Street",
            "geographic_unit_id": kumba1["geographic_unit_id"],
        },
    )
    assert reg.status_code == 200, reg.text
    payer = reg.json()

    admin_token = _login(client, "kumba1_admin", "council123")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    revenues = client.get("/api/v1/revenue-types", headers=admin_headers)
    assert revenues.status_code == 200, revenues.text
    revenue = revenues.json()[0]

    obl = client.post(
        "/api/v1/obligations",
        headers=admin_headers,
        json={
            "payer_id": payer["payer_id"],
            "revenue_type_id": revenue["revenue_type_id"],
            "amount": "25000",
            "description": "Test Levy",
        },
    )
    assert obl.status_code == 200, obl.text
    obligation = obl.json()
    geo_at_pay = obligation["geographic_unit_id"]
    tenant_at_pay = obligation["tenant_id"]

    token = _login(client, username, "payer123")
    headers = {"Authorization": f"Bearer {token}"}

    resolved = client.post(
        "/api/v1/payments/resolve",
        headers=headers,
        json={"obligation_id": obligation["obligation_id"], "payment_channel": "MOBILE_MONEY"},
    )
    assert resolved.status_code == 200, resolved.text
    assert Decimal(str(resolved.json()["service_fee"])) >= 0

    key = f"test-key-{suffix}"
    init = client.post(
        "/api/v1/payments/initiate",
        headers=headers,
        json={
            "obligation_id": obligation["obligation_id"],
            "payment_channel": "MOBILE_MONEY",
            "idempotency_key": key,
        },
    )
    assert init.status_code == 200, init.text
    txn_id = init.json()["transaction_id"]

    init2 = client.post(
        "/api/v1/payments/initiate",
        headers=headers,
        json={
            "obligation_id": obligation["obligation_id"],
            "payment_channel": "MOBILE_MONEY",
            "idempotency_key": key,
        },
    )
    assert init2.json()["transaction_id"] == txn_id

    conf = client.post(f"/api/v1/payments/{txn_id}/confirm", headers=headers)
    assert conf.status_code == 200, conf.text
    detail = conf.json()
    assert detail["status"] == "SETTLED"
    assert detail["transaction_geographic_unit_id"] == geo_at_pay
    assert detail["transaction_tenant_id"] == tenant_at_pay
    assert detail["receipt_number"]

    change = client.post(
        "/api/v1/payers/me/operating-area/change",
        headers=headers,
        json={"geographic_unit_id": kumba3["geographic_unit_id"], "reason": "Business relocated"},
    )
    assert change.status_code == 200, change.text

    again = client.get(f"/api/v1/payments/{txn_id}", headers=headers)
    assert again.json()["transaction_geographic_unit_id"] == geo_at_pay
    assert again.json()["transaction_tenant_id"] == tenant_at_pay

    receipt_id = detail["receipt_id"]
    receipt = client.get(f"/api/v1/receipts/{receipt_id}", headers=headers)
    token_v = receipt.json()["verification_token"]
    verify = client.get(f"/api/v1/public/verify/{token_v}")
    assert verify.status_code == 200
    assert verify.json()["verified"] is True
