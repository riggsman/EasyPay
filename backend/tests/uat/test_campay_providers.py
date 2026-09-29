"""UAT for Campay routing, encrypted providers, and settlement payout options."""
from app.core.encryption import decrypt_json, encrypt_json, is_encrypted


def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_encryption_roundtrip():
    blob = encrypt_json({"password": "secret", "username": "demo"})
    assert is_encrypted(blob)
    assert decrypt_json(blob)["password"] == "secret"


def test_provider_config_restricted_to_system_admin(client):
    staff = _login(client, "kumba1_admin", "council123")
    denied = client.get("/api/v1/providers", headers={"Authorization": f"Bearer {staff}"})
    assert denied.status_code == 403

    admin = _login(client, "admin", "admin123")
    headers = {"Authorization": f"Bearer {admin}"}
    listed = client.get("/api/v1/providers", headers=headers)
    assert listed.status_code == 200, listed.text

    saved = client.put(
        "/api/v1/providers/campay",
        headers=headers,
        json={
            "enabled": True,
            "display_name": "Campay",
            "settings": {"username": "u1", "password": "p1", "mock": True, "base_url": "https://demo.campay.net/api"},
            "public_meta": {"environment": "sandbox"},
        },
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["enabled"] is True
    assert body["settings"].get("password_configured") is True
    assert "*" in (body["settings"].get("password") or "*")

    email = client.put(
        "/api/v1/providers/email",
        headers=headers,
        json={
            "enabled": True,
            "settings": {"smtp_host": "smtp.example.com", "smtp_password": "mail-secret", "smtp_user": "ops@easypay.local"},
        },
    )
    assert email.status_code == 200, email.text
    assert email.json()["settings"].get("smtp_password_configured") is True

    wa = client.put(
        "/api/v1/providers/whatsapp",
        headers=headers,
        json={"enabled": True, "settings": {"api_url": "https://wa.example/api", "api_key": "wa-secret"}},
    )
    assert wa.status_code == 200, wa.text


def test_campay_collect_and_disburse_endpoints(client):
    token = _login(client, "admin", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    client.put(
        "/api/v1/providers/campay",
        headers=headers,
        json={"enabled": True, "settings": {"mock": True, "username": "demo", "password": "demo"}},
    )
    collect = client.post(
        "/api/v1/campay/collect",
        headers=headers,
        json={
            "amount": 1000,
            "phone_number": "237670000001",
            "description": "Test collect",
            "external_reference": "EXT-COLLECT-1",
        },
    )
    assert collect.status_code == 200, collect.text
    assert collect.json()["provider_reference"]
    assert collect.json()["operation"] == "COLLECT"

    withdraw = client.post(
        "/api/v1/campay/withdraw",
        headers=headers,
        json={
            "amount": 500,
            "phone_number": "237670000001",
            "description": "Test withdraw",
            "external_reference": "EXT-WD-1",
        },
    )
    assert withdraw.status_code == 200, withdraw.text

    bank = client.post(
        "/api/v1/campay/bank-transfer",
        headers=headers,
        json={
            "amount": 500,
            "account_number": "100200300",
            "account_name": "Kumba 1 Council",
            "bank_code": "BIC001",
            "description": "Test bank",
            "external_reference": "EXT-BANK-1",
        },
    )
    assert bank.status_code == 200, bank.text
    assert bank.json()["payout_method"] == "BANK"
