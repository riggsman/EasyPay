"""UAT for financial ops console APIs."""


def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_uat_ops_console_endpoints_for_tenant_admin(client):
    token = _login(client, "kumba1_admin", "council123")
    headers = {"Authorization": f"Bearer {token}"}
    for path in [
        "/api/v1/ops/alerts",
        "/api/v1/ops/payers",
        "/api/v1/ops/collections",
        "/api/v1/ops/fees",
        "/api/v1/ops/commissions",
        "/api/v1/ops/staff-users",
        "/api/v1/ops/roles",
        "/api/v1/ops/config",
        "/api/v1/ops/audit",
        "/api/v1/ops/ledger/postings",
        "/api/v1/ops/reconciliation",
        "/api/v1/ops/statements/tenant",
    ]:
        r = client.get(path, headers=headers)
        assert r.status_code == 200, f"{path} -> {r.status_code} {r.text}"


def test_uat_ops_alerts_for_platform_admin(client):
    token = _login(client, "admin", "admin123")
    r = client.get("/api/v1/ops/alerts", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert "pending_transactions" in body
