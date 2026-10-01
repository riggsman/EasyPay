"""UAT for platform-configurable client cache TTL."""


def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_uat_cache_ttl_header_on_responses(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.headers.get("X-EasyPay-Cache-TTL") == "900"


def test_uat_platform_admin_can_increase_client_cache_ttl(client):
    token = _login(client, "admin", "admin123")
    headers = {"Authorization": f"Bearer {token}"}

    current = client.get("/api/v1/ops/client-cache-settings", headers=headers)
    assert current.status_code == 200, current.text
    body = current.json()
    assert body["ttl_seconds"] == 900
    assert body["min_ttl_seconds"] == 900
    assert body["default_ttl_seconds"] == 900

    too_low = client.put(
        "/api/v1/ops/client-cache-settings",
        headers=headers,
        json={"ttl_minutes": 5},
    )
    assert too_low.status_code == 400

    updated = client.put(
        "/api/v1/ops/client-cache-settings",
        headers=headers,
        json={"ttl_minutes": 30},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["ttl_minutes"] == 30
    assert updated.json()["ttl_seconds"] == 1800
    assert updated.headers.get("X-EasyPay-Cache-TTL") == "1800"

    # Subsequent responses advertise the new TTL for clients to adopt.
    health = client.get("/health")
    assert health.headers.get("X-EasyPay-Cache-TTL") == "1800"

    # Restore default for other suites
    restore = client.put(
        "/api/v1/ops/client-cache-settings",
        headers=headers,
        json={"ttl_minutes": 15},
    )
    assert restore.status_code == 200, restore.text
    assert restore.json()["ttl_seconds"] == 900
