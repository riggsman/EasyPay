from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.transaction import Transaction
from app.models.payer import Payer


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_and_geography(client):
    token = _login(client, "admin", "admin123")
    r = client.get("/api/v1/geography/children", headers={"Authorization": f"Bearer {token}"})
    # roots without parent
    r = client.get("/api/v1/geography/children")
    assert r.status_code == 200
    assert any(u["unit_code"] == "CM" for u in r.json())


def test_payer_payment_and_history_invariant(client):
    token = _login(client, "abctrading", "payer123")
    headers = {"Authorization": f"Bearer {token}"}

    obl = client.get("/api/v1/obligations", headers=headers)
    assert obl.status_code == 200
    obligations = obl.json()
    assert len(obligations) >= 1
    target = next(o for o in obligations if float(o["balance"]) > 0)
    geo_at_pay = target["geographic_unit_id"]
    tenant_at_pay = target["tenant_id"]

    resolved = client.post(
        "/api/v1/payments/resolve",
        headers=headers,
        json={"obligation_id": target["obligation_id"], "payment_channel": "MOBILE_MONEY"},
    )
    assert resolved.status_code == 200, resolved.text
    assert Decimal(str(resolved.json()["service_fee"])) >= 0

    init = client.post(
        "/api/v1/payments/initiate",
        headers=headers,
        json={
            "obligation_id": target["obligation_id"],
            "payment_channel": "MOBILE_MONEY",
            "idempotency_key": "test-key-history-001",
        },
    )
    assert init.status_code == 200, init.text
    txn_id = init.json()["transaction_id"]

    # Idempotency
    init2 = client.post(
        "/api/v1/payments/initiate",
        headers=headers,
        json={
            "obligation_id": target["obligation_id"],
            "payment_channel": "MOBILE_MONEY",
            "idempotency_key": "test-key-history-001",
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

    # Change zone to Kumba 3
    kids = client.get("/api/v1/geography/children")
    # find Kumba town then Kumba 3
    cm = client.get("/api/v1/geography/children").json()[0]
    regions = client.get(f"/api/v1/geography/children?parent_id={cm['geographic_unit_id']}").json()
    divisions = client.get(f"/api/v1/geography/children?parent_id={regions[0]['geographic_unit_id']}").json()
    towns = client.get(f"/api/v1/geography/children?parent_id={divisions[0]['geographic_unit_id']}").json()
    councils = client.get(f"/api/v1/geography/children?parent_id={towns[0]['geographic_unit_id']}").json()
    kumba3 = next(c for c in councils if c["unit_code"] == "KUMBA-03")

    change = client.post(
        "/api/v1/payers/me/operating-area/change",
        headers=headers,
        json={"geographic_unit_id": kumba3["geographic_unit_id"], "reason": "Business relocated"},
    )
    assert change.status_code == 200, change.text

    # Historical transaction must still show Kumba 1 snapshot
    again = client.get(f"/api/v1/payments/{txn_id}", headers=headers)
    assert again.json()["transaction_geographic_unit_id"] == geo_at_pay
    assert again.json()["transaction_tenant_id"] == tenant_at_pay

    # Public verify
    receipt_id = detail["receipt_id"]
    receipt = client.get(f"/api/v1/receipts/{receipt_id}", headers=headers)
    token_v = receipt.json()["verification_token"]
    verify = client.get(f"/api/v1/public/verify/{token_v}")
    assert verify.status_code == 200
    assert verify.json()["verified"] is True
