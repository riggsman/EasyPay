"""Council credit failure, retries, and platform manual intervention."""

import subprocess
import sys
from pathlib import Path

from app.db.session import SessionLocal
from app.models.tenant import Tenant
from app.models.transaction import Transaction
from app.services.payments import DEFAULT_CREDIT_MAX_RETRIES, credit_max_retries


def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _ensure_seed_demos():
    root = Path(__file__).resolve().parents[2]
    subprocess.run([sys.executable, str(root / "scripts" / "seed.py")], check=True, cwd=str(root))


def _find_ref(client, headers, ref):
    res = client.get("/api/v1/payments?page=1&page_size=100&q=" + ref, headers=headers)
    assert res.status_code == 200, res.text
    items = res.json().get("items") or []
    return next((i for i in items if i.get("transaction_reference") == ref), None)


def test_credit_fail_demo_exposes_reason_and_retry(client):
    _ensure_seed_demos()
    token = _login(client, "admin", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    row = _find_ref(client, headers, "TXN-DEMO-CREDIT-FAIL")
    assert row, "expected seeded credit-fail demo"
    assert row["status"] == "FAILED"
    assert row.get("failure_stage") == "CREDIT"
    assert row.get("failure_reason")

    detail = client.get(f"/api/v1/payments/{row['transaction_id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["credit_recovery"]["can_retry"] is True
    assert body["credit_recovery"]["failure_stage"] == "CREDIT"

    drill = client.get(f"/api/v1/ops/drill/transaction/{row['transaction_id']}", headers=headers)
    assert drill.status_code == 200, drill.text
    assert drill.json().get("credit_recovery", {}).get("can_retry") is True


def test_retry_exhaustion_moves_to_manual_intervention(client):
    _ensure_seed_demos()
    db = SessionLocal()
    try:
        txn = db.query(Transaction).filter(Transaction.transaction_reference == "TXN-DEMO-CREDIT-FAIL").first()
        assert txn
        max_r = credit_max_retries(db)
        txn.credit_retry_count = max(0, max_r - 1)
        txn.credit_destination = "670000000"
        txn.status = "FAILED"
        txn.failure_stage = "CREDIT"
        db.commit()
        txn_id = txn.transaction_id
    finally:
        db.close()

    token = _login(client, "kumba1_admin", "council123")
    headers = {"Authorization": f"Bearer {token}"}
    retry = client.post(f"/api/v1/payments/{txn_id}/retry-credit", headers=headers)
    assert retry.status_code == 200, retry.text
    body = retry.json()
    assert body["status"] == "MANUAL_INTERVENTION"
    assert body["credit_recovery"]["needs_manual_intervention"] is True
    assert body["credit_retry_count"] >= DEFAULT_CREDIT_MAX_RETRIES


def test_platform_manual_credit_autofill_and_settle(client):
    _ensure_seed_demos()
    db = SessionLocal()
    try:
        txn = db.query(Transaction).filter(Transaction.transaction_reference == "TXN-DEMO-CREDIT-MANUAL").first()
        assert txn
        tenant = db.get(Tenant, txn.transaction_tenant_id)
        txn.credit_destination = tenant.momo_number or "670100001"
        txn.status = "MANUAL_INTERVENTION"
        txn.failure_stage = "CREDIT"
        db.commit()
        txn_id = txn.transaction_id
    finally:
        db.close()

    token = _login(client, "admin", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    ctx = client.get(f"/api/v1/payments/{txn_id}/credit-recovery", headers=headers)
    assert ctx.status_code == 200, ctx.text
    payload = ctx.json()
    assert payload["needs_manual_intervention"] is True
    assert payload["net_credit_amount"]
    assert payload["council_name"]
    assert payload["momo_number"]
    assert payload["warnings"]

    denied = client.post(
        f"/api/v1/payments/{txn_id}/manual-credit",
        headers=headers,
        json={"confirm": False, "payout_method": "MOMO", "momo_number": payload["momo_number"]},
    )
    assert denied.status_code == 422

    ok = client.post(
        f"/api/v1/payments/{txn_id}/manual-credit",
        headers=headers,
        json={
            "confirm": True,
            "payout_method": "MOMO",
            "momo_number": payload["momo_number"],
            "amount": payload["net_credit_amount"],
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "SETTLED"


def test_payer_sees_debit_failure_reason(client):
    _ensure_seed_demos()
    token = _login(client, "abctrading", "payer123")
    headers = {"Authorization": f"Bearer {token}"}
    row = _find_ref(client, headers, "TXN-DEMO-DEBIT-FAIL")
    assert row
    detail = client.get(f"/api/v1/payments/{row['transaction_id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["status"] == "FAILED"
    assert body["failure_stage"] == "DEBIT"
    assert body.get("failure_reason")
    assert body.get("credit_recovery") is None
    statuses = [e["to_status"] for e in body.get("events") or []]
    assert statuses == ["INITIATED", "PROCESSING", "FAILED"]
    assert statuses[-1] == "FAILED"
    assert "CREDITED" not in statuses and "SETTLED" not in statuses
    failed = body["events"][-1]
    assert failed.get("label") == "Customer account debit failed"
    assert "debit" in (failed.get("note") or body["failure_reason"]).lower() or "declined" in (
        failed.get("note") or body["failure_reason"]
    ).lower()


def test_live_payer_debit_failure_stops_after_debit_stage(client):
    """Simulate Campay collect decline → FAILED right after debiting stage with reason."""
    from app.db.base import new_id
    from app.db.session import SessionLocal
    from app.models.obligation import Obligation
    from app.models.payer import Payer
    from app.services.payments import initiate_payment
    from app.schemas.common import PaymentInitiateRequest
    from unittest.mock import patch
    from app.services.providers.campay import CampayResult

    from app.models.user import User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "abctrading").first()
        assert user
        payer = db.query(Payer).filter(Payer.user_id == user.user_id).first()
        assert payer
        obl = (
            db.query(Obligation)
            .filter(Obligation.payer_id == payer.payer_id, Obligation.status.in_(["DUE", "PARTIAL", "OVERDUE"]))
            .first()
        )
        if not obl:
            obl = db.query(Obligation).filter(Obligation.payer_id == payer.payer_id).first()
        assert obl
        key = f"sim-debit-fail-{new_id('')[-8:]}"
        with patch("app.services.providers.campay.CampayClient.collect") as collect:
            collect.return_value = CampayResult(
                ok=False,
                reference=None,
                status="FAILED",
                raw={},
                error="Payer debit failed: MoMo wallet declined collection (insufficient funds)",
            )
            txn = initiate_payment(
                db,
                payer,
                PaymentInitiateRequest(
                    obligation_id=obl.obligation_id,
                    payment_channel="MOBILE_MONEY",
                    phone_number=payer.phone_number or "670000001",
                    idempotency_key=key,
                ),
                actor_user_id=payer.user_id,
            )
        assert txn.status == "FAILED"
        assert txn.failure_stage == "DEBIT"
        assert txn.failure_reason
        txn_id = txn.transaction_id
    finally:
        db.close()

    token = _login(client, "abctrading", "payer123")
    headers = {"Authorization": f"Bearer {token}"}
    detail = client.get(f"/api/v1/payments/{txn_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    statuses = [e["to_status"] for e in body["events"]]
    assert statuses[:3] == ["INITIATED", "PROCESSING", "FAILED"]
    assert body["events"][-1]["label"] == "Customer account debit failed"
    assert "insufficient" in (body["failure_reason"] or "").lower() or "declined" in (
        body["failure_reason"] or ""
    ).lower()
