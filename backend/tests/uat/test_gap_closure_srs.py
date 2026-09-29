"""SRS gap-closure UAT: server search, exports, payer notifications, platform admin access."""


def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_server_search_on_payments_and_receipts(client):
    token = _login(client, "kumba1_admin", "council123")
    headers = {"Authorization": f"Bearer {token}"}
    pay = client.get("/api/v1/payments?q=TXN&page=1&page_size=5", headers=headers)
    assert pay.status_code == 200, pay.text
    body = pay.json()
    assert "items" in body and "total" in body

    rcpt = client.get("/api/v1/receipts?q=RCPT&page=1&page_size=5", headers=headers)
    assert rcpt.status_code == 200, rcpt.text
    assert "items" in rcpt.json()

    ledger = client.get("/api/v1/ops/ledger/postings?q=Payment&page=1&page_size=5", headers=headers)
    assert ledger.status_code == 200, ledger.text
    assert "items" in ledger.json()


def test_exports_audit_and_settlements(client):
    token = _login(client, "kumba1_admin", "council123")
    headers = {"Authorization": f"Bearer {token}"}
    audit = client.get("/api/v1/ops/exports/audit.csv", headers=headers)
    assert audit.status_code == 200
    assert "entity_type" in audit.text
    settles = client.get("/api/v1/ops/exports/settlements.csv", headers=headers)
    assert settles.status_code == 200
    assert "settlement_reference" in settles.text


def test_payer_notifications_inbox(client):
    token = _login(client, "abctrading", "payer123")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/ops/my-notifications?page=1&page_size=10", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body


def test_sms_provider_config_admin_only(client):
    staff = _login(client, "kumba1_admin", "council123")
    denied = client.put(
        "/api/v1/providers/sms",
        headers={"Authorization": f"Bearer {staff}"},
        json={"enabled": True, "settings": {"api_url": "https://sms.example", "api_key": "k"}},
    )
    assert denied.status_code == 403

    admin = _login(client, "admin", "admin123")
    ok = client.put(
        "/api/v1/providers/sms",
        headers={"Authorization": f"Bearer {admin}"},
        json={"enabled": True, "settings": {"api_url": "https://sms.example", "api_key": "k"}},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["settings"].get("api_key_configured") is True
