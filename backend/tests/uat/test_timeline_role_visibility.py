"""Transaction timeline order and role-scoped intermediary states."""


def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _statuses(events):
    return [e["to_status"] for e in events]


def _settled_txn_id(client, headers):
    res = client.get("/api/v1/payments?page=1&page_size=20&status=SETTLED", headers=headers)
    assert res.status_code == 200, res.text
    items = res.json().get("items") or []
    assert items, "expected settled payments in seed data"
    return items[0]["transaction_id"]


def test_payer_timeline_order_and_hides_credited(client):
    token = _login(client, "abctrading", "payer123")
    headers = {"Authorization": f"Bearer {token}"}
    txn_id = _settled_txn_id(client, headers)

    detail = client.get(f"/api/v1/payments/{txn_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    statuses = _statuses(detail.json().get("events") or [])
    assert statuses[0] == "INITIATED"
    assert statuses[-1] == "SETTLED"
    assert "DEBITED" in statuses
    assert "CREDITED" not in statuses
    assert _is_ordered(statuses)

    labels = [e.get("label") for e in detail.json()["events"]]
    assert labels[0] == "Initiated"
    assert labels[-1] == "Settlement completed"
    assert not any((e.get("note") or "").lower().startswith("campay collect") for e in detail.json()["events"])


def test_council_timeline_hides_debited(client):
    token = _login(client, "kumba1_admin", "council123")
    headers = {"Authorization": f"Bearer {token}"}
    txn_id = _settled_txn_id(client, headers)

    detail = client.get(f"/api/v1/payments/{txn_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    statuses = _statuses(detail.json().get("events") or [])
    assert statuses[0] == "INITIATED"
    assert statuses[-1] == "SETTLED"
    assert "CREDITED" in statuses
    assert "DEBITED" not in statuses
    assert _is_ordered(statuses)


def test_platform_timeline_sees_all_states(client):
    token = _login(client, "admin", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    txn_id = _settled_txn_id(client, headers)

    detail = client.get(f"/api/v1/payments/{txn_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    statuses = _statuses(detail.json().get("events") or [])
    for expected in ("INITIATED", "PROCESSING", "DEBITED", "CREDITED", "SETTLED"):
        assert expected in statuses
    assert statuses[0] == "INITIATED"
    assert statuses[-1] == "SETTLED"
    assert _is_ordered(statuses)

    drill = client.get(f"/api/v1/ops/drill/transaction/{txn_id}", headers=headers)
    assert drill.status_code == 200, drill.text
    drill_statuses = _statuses(drill.json().get("events") or [])
    assert "DEBITED" in drill_statuses and "CREDITED" in drill_statuses
    assert drill_statuses[0] == "INITIATED"
    assert drill_statuses[-1] == "SETTLED"


_ORDER = {
    "INITIATED": 0,
    "PROCESSING": 1,
    "DEBITED": 2,
    "CREDITED": 3,
    "SETTLED": 4,
    "FAILED": 4,
    "REJECTED": 4,
}


def _is_ordered(statuses):
    ranks = [_ORDER[s] for s in statuses if s in _ORDER]
    return ranks == sorted(ranks)
