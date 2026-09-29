"""UAT for paginated list APIs and notification modules."""


def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _assert_page_shape(body):
    assert "items" in body
    assert "page" in body
    assert "page_size" in body
    assert "total" in body
    assert "total_pages" in body


def test_uat_paginated_ops_lists(client):
    token = _login(client, "kumba1_admin", "council123")
    headers = {"Authorization": f"Bearer {token}"}
    for path in [
        "/api/v1/ops/payers?page=1&page_size=5",
        "/api/v1/ops/collections?page=1&page_size=5",
        "/api/v1/ops/audit?page=1&page_size=5",
        "/api/v1/payments?page=1&page_size=5",
        "/api/v1/obligations?page=1&page_size=5",
    ]:
        r = client.get(path, headers=headers)
        assert r.status_code == 200, f"{path} -> {r.text}"
        _assert_page_shape(r.json())


def test_uat_notification_settings_and_sms_toggle(client):
    token = _login(client, "admin", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/ops/notifications/settings", headers=headers)
    assert r.status_code == 200
    before = r.json()
    assert "sms_enabled" in before
    assert before["sms_master_switch"] is False

    off = client.put(
        "/api/v1/ops/notifications/settings",
        headers=headers,
        json={"sms_enabled": False, "email_enabled": True},
    )
    assert off.status_code == 200
    assert off.json()["sms_enabled"] is False

    log = client.get("/api/v1/ops/notifications/delivery-log?page=1&page_size=10", headers=headers)
    assert log.status_code == 200
    _assert_page_shape(log.json())
