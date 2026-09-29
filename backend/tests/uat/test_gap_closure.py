"""UAT covering gap-closure APIs for ops console completeness."""


def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_uat_search_and_drill_and_exports(client):
    token = _login(client, "kumba1_admin", "council123")
    headers = {"Authorization": f"Bearer {token}"}

    search = client.get("/api/v1/ops/search?q=TXN", headers=headers)
    assert search.status_code == 200
    body = search.json()
    assert "results" in body

    payments = client.get("/api/v1/payments", headers=headers)
    assert payments.status_code == 200
    rows = payments.json().get("items", payments.json())
    if rows:
        drill = client.get(f"/api/v1/ops/drill/transaction/{rows[0]['transaction_id']}", headers=headers)
        assert drill.status_code == 200, drill.text
        chain = drill.json()
        assert "transaction" in chain
        assert "fee_commission" in chain
        assert "ledger" in chain
        assert "audit" in chain

    alerts = client.get("/api/v1/ops/alerts", headers=headers)
    assert alerts.status_code == 200
    assert "items" in alerts.json()

    csv_r = client.get("/api/v1/ops/exports/collections.csv", headers=headers)
    assert csv_r.status_code == 200
    assert "transaction_reference" in csv_r.text

    xlsx = client.get("/api/v1/ops/exports/collections.xlsx", headers=headers)
    assert xlsx.status_code == 200
    assert xlsx.headers["content-type"].startswith("application/vnd.openxmlformats")


def test_uat_payer_statement_and_own_drill(client):
    token = _login(client, "abctrading", "payer123")
    headers = {"Authorization": f"Bearer {token}"}
    stmt = client.get("/api/v1/ops/payer-statement", headers=headers)
    assert stmt.status_code == 200
    payments = client.get("/api/v1/payments", headers=headers)
    rows = payments.json().get("items", payments.json())
    if rows:
        drill = client.get(f"/api/v1/ops/drill/transaction/{rows[0]['transaction_id']}", headers=headers)
        assert drill.status_code == 200


def test_uat_create_commission_and_staff(client):
    token = _login(client, "kumba1_admin", "council123")
    headers = {"Authorization": f"Bearer {token}"}
    comm = client.post(
        "/api/v1/ops/commissions",
        headers=headers,
        json={"commission_type": "PERCENT", "commission_value": "2.5"},
    )
    assert comm.status_code == 200, comm.text
