def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_payer_payment_list_hides_commission(client):
    token = _login(client, "abctrading", "payer123")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/payments?page=1&page_size=10", headers=headers)
    assert res.status_code == 200, res.text
    items = res.json().get("items") or []
    assert items, "expected payer payments"
    for item in items:
        assert item.get("commission_amount") is None


def test_payer_payment_detail_hides_commission(client):
    token = _login(client, "abctrading", "payer123")
    headers = {"Authorization": f"Bearer {token}"}
    listing = client.get("/api/v1/payments?page=1&page_size=1", headers=headers)
    txn_id = listing.json()["items"][0]["transaction_id"]
    detail = client.get(f"/api/v1/payments/{txn_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body.get("commission_amount") is None

    drill = client.get(f"/api/v1/ops/drill/transaction/{txn_id}", headers=headers)
    assert drill.status_code == 200, drill.text
    fc = drill.json().get("fee_commission") or {}
    assert "commission_amount" not in fc
    assert "net_to_tenant" not in fc
    assert "service_fee" in fc


def test_admin_payment_still_includes_commission(client):
    token = _login(client, "admin", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/payments?page=1&page_size=5&status=SETTLED", headers=headers)
    assert res.status_code == 200, res.text
    items = res.json().get("items") or []
    assert items
    assert items[0].get("commission_amount") is not None
