from decimal import Decimal


def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_admin_can_configure_history_export_fee(client):
    token = _login(client, "admin", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    got = client.get("/api/v1/ops/history-export-settings", headers=headers)
    assert got.status_code == 200, got.text
    updated = client.put(
        "/api/v1/ops/history-export-settings",
        headers=headers,
        json={"fee_amount": "750", "free_downloads": 2, "currency": "XAF"},
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert Decimal(str(body["fee_amount"])) == Decimal("750")
    assert body["free_downloads"] == 2


def test_payer_free_then_charged_history_export(client):
    admin = _login(client, "admin", "admin123")
    admin_headers = {"Authorization": f"Bearer {admin}"}
    cfg = client.put(
        "/api/v1/ops/history-export-settings",
        headers=admin_headers,
        json={"fee_amount": "500", "free_downloads": 2, "currency": "XAF"},
    )
    assert cfg.status_code == 200, cfg.text

    token = _login(client, "abctrading", "payer123")
    headers = {"Authorization": f"Bearer {token}"}

    quote1 = client.get("/api/v1/payers/me/history-exports/quote", headers=headers)
    assert quote1.status_code == 200, quote1.text
    q1 = quote1.json()
    assert q1["free_downloads"] == 2
    assert q1["free_downloads_remaining"] >= 0

    # Consume free downloads up to allowance (fresh payer usage may already have some)
    remaining = q1["free_downloads_remaining"]
    for i in range(remaining):
        r = client.post(
            "/api/v1/payers/me/history-exports",
            headers=headers,
            json={"date_from": "2026-01-01T00:00:00", "date_to": "2026-12-31T23:59:59"},
        )
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
        assert r.headers.get("X-EasyPay-Was-Free") == "true"

    quote2 = client.get("/api/v1/payers/me/history-exports/quote", headers=headers).json()
    assert quote2["free_downloads_remaining"] == 0
    assert quote2["will_charge"] is True

    charged = client.post(
        "/api/v1/payers/me/history-exports",
        headers=headers,
        json={
            "date_from": "2026-01-01T00:00:00",
            "date_to": "2026-12-31T23:59:59",
            "phone_number": "670000001",
        },
    )
    assert charged.status_code == 200, charged.text
    assert charged.content[:4] == b"%PDF"
    assert charged.headers.get("X-EasyPay-Was-Free") == "false"
    assert Decimal(str(charged.headers.get("X-EasyPay-Fee-Amount"))) == Decimal("500")
