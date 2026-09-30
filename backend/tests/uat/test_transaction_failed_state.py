"""FAILED is a peer terminal outcome to SETTLED."""

from app.db.base import new_id, utcnow
from app.db.session import SessionLocal
from app.models.transaction import Transaction
from app.services.payments import (
    TIMELINE_STATUS_ORDER,
    advance_transaction,
    normalize_transaction_status,
)


def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_failed_shares_terminal_stage_with_settled():
    assert TIMELINE_STATUS_ORDER["FAILED"] == TIMELINE_STATUS_ORDER["SETTLED"]
    assert normalize_transaction_status("REJECTED") == "FAILED"


def test_processing_can_fail_instead_of_settle(client):
    token = _login(client, "abctrading", "payer123")
    headers = {"Authorization": f"Bearer {token}"}

    settled = client.get("/api/v1/payments?page=1&page_size=1&status=SETTLED", headers=headers)
    assert settled.status_code == 200, settled.text
    seed = settled.json()["items"][0]

    db = SessionLocal()
    try:
        template = db.get(Transaction, seed["transaction_id"])
        assert template is not None
        txn = Transaction(
            transaction_id=new_id("txn_"),
            transaction_reference=f"TXN-FAIL-{new_id('')[-6:]}",
            correlation_id=new_id("cor_"),
            idempotency_key=new_id("idem_"),
            payer_id=template.payer_id,
            transaction_tenant_id=template.transaction_tenant_id,
            transaction_geographic_unit_id=template.transaction_geographic_unit_id,
            obligation_id=template.obligation_id,
            revenue_type_id=template.revenue_type_id,
            amount=template.amount,
            service_fee=template.service_fee,
            commission_amount=template.commission_amount,
            total_amount=template.total_amount,
            currency=template.currency,
            payment_channel=template.payment_channel or "MOBILE_MONEY",
            payment_provider=template.payment_provider,
            status="PROCESSING",
            initiated_at=utcnow(),
        )
        db.add(txn)
        db.commit()
        txn_id = txn.transaction_id

        advanced = advance_transaction(db, txn, "FAILED", note="Simulated provider failure")
        assert advanced.status == "FAILED"
    finally:
        db.close()

    detail = client.get(f"/api/v1/payments/{txn_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["status"] == "FAILED"
    statuses = [e["to_status"] for e in body.get("events") or []]
    assert statuses[-1] == "FAILED"
    failed_event = next(e for e in body["events"] if e["to_status"] == "FAILED")
    assert failed_event.get("label") == "Payment failed"


def test_legacy_rejected_alias_advances_as_failed(client):
    token = _login(client, "admin", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    settled = client.get("/api/v1/payments?page=1&page_size=1&status=SETTLED", headers=headers)
    seed = settled.json()["items"][0]

    db = SessionLocal()
    try:
        template = db.get(Transaction, seed["transaction_id"])
        txn = Transaction(
            transaction_id=new_id("txn_"),
            transaction_reference=f"TXN-REJ-{new_id('')[-6:]}",
            correlation_id=new_id("cor_"),
            idempotency_key=new_id("idem_"),
            payer_id=template.payer_id,
            transaction_tenant_id=template.transaction_tenant_id,
            transaction_geographic_unit_id=template.transaction_geographic_unit_id,
            obligation_id=template.obligation_id,
            revenue_type_id=template.revenue_type_id,
            amount=template.amount,
            service_fee=template.service_fee,
            commission_amount=template.commission_amount,
            total_amount=template.total_amount,
            currency=template.currency,
            payment_channel="MOBILE_MONEY",
            status="DEBITED",
            initiated_at=utcnow(),
        )
        db.add(txn)
        db.commit()
        # Callers may still pass REJECTED; service normalizes to FAILED
        advanced = advance_transaction(db, txn, "REJECTED", note="Legacy reject path")
        assert advanced.status == "FAILED"
        txn_id = advanced.transaction_id
    finally:
        db.close()

    detail = client.get(f"/api/v1/payments/{txn_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == "FAILED"
