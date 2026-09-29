"""User acceptance tests for core EasyPay financial flows."""
from decimal import Decimal
import uuid


def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def test_uat_platform_admin_can_list_tenants(client):
    tokens = _login(client, "admin", "admin123")
    assert tokens["user_type"] == "PLATFORM_ADMIN"
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    r = client.get("/api/v1/tenants", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert r.status_code == 200
    assert len(r.json()) >= 3


def test_uat_refresh_token_issues_new_access(client):
    tokens = _login(client, "admin", "admin123")
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    assert r.json()["access_token"]
    assert r.json()["refresh_token"]


def test_uat_tenant_isolation_blocks_cross_council(client):
    tokens = _login(client, "kumba1_admin", "council123")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    tenants = client.get("/api/v1/tenants", headers=headers).json()
    assert len(tenants) == 1
    assert tenants[0]["tenant_code"] == "KUMBA1"


def test_uat_argon2_login_works_for_seed_users(client):
    for user, pwd in [("admin", "admin123"), ("abctrading", "payer123"), ("kumba1_admin", "council123")]:
        tokens = _login(client, user, pwd)
        assert tokens["access_token"]


def test_uat_public_verify_rejects_unknown(client):
    r = client.post("/api/v1/public/verify", json={"receipt_number": "RCPT-DOES-NOT-EXIST"})
    assert r.status_code == 200
    assert r.json()["verified"] is False
