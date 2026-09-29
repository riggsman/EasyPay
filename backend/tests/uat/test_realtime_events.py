"""Realtime envelope and alerts digest tests."""

from app.realtime import schemas as evt
from app.services.alerts import alerts_digest


def test_event_envelope_shape():
    msg = evt.envelope("transaction.status_changed", {"status": "SETTLED"}, tenant_id="ten_1", entity_id="txn_1")
    assert msg["schema_version"] == 1
    assert msg["type"] == "transaction.status_changed"
    assert msg["tenant_id"] == "ten_1"
    assert "event_id" in msg
    assert "occurred_at" in msg
    assert msg["payload"]["status"] == "SETTLED"


def test_alerts_digest_stable():
    snap = {"pending_transactions": 2, "rejected_transactions": 1, "settlements_awaiting_approval": 0}
    assert alerts_digest(snap) == "p2r1s0"
