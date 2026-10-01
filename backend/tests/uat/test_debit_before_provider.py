"""Enforce: part-2 provider calls only after payer MoMo debit is confirmed."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from app.db.session import SessionLocal
from app.models.provider import ProviderPaymentIntent
from app.models.transaction import Transaction
from app.services.payments import _attempt_council_credit, confirm_payer_debit
from app.services.utilities import _attempt_utility_provider_credit, ensure_sample_utility_services


def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _ensure_utilities():
    root = Path(__file__).resolve().parents[2]
    subprocess.run([sys.executable, str(root / "scripts" / "migrate_utilities.py")], check=True, cwd=str(root))
    db = SessionLocal()
    try:
        ensure_sample_utility_services(db)
    finally:
        db.close()


def test_council_credit_blocked_before_debit_confirmed(client):
    token = _login(client, "abctrading", "payer123")
    headers = {"Authorization": f"Bearer {token}"}
    due = client.get("/api/v1/obligations?status=DUE", headers=headers)
    assert due.status_code == 200
    items = due.json() if isinstance(due.json(), list) else due.json().get("items") or []
    assert items, "need a due obligation"
    obl = items[0]
    init = client.post(
        "/api/v1/payments/initiate",
        headers=headers,
        json={
            "obligation_id": obl["obligation_id"],
            "payment_channel": "MOBILE_MONEY",
            "phone_number": "670000001",
            "idempotency_key": f"debit-guard-levy-{__import__('uuid').uuid4().hex[:12]}",
        },
    )
    assert init.status_code == 200, init.text
    txn_id = init.json()["transaction_id"]

    db = SessionLocal()
    try:
        txn = db.get(Transaction, txn_id)
        assert txn.status in ("PROCESSING", "INITIATED", "FAILED")
        # Force a pre-debit state and ensure council credit refuses provider call
        if txn.status != "PROCESSING":
            txn.status = "PROCESSING"
            db.commit()
            db.refresh(txn)
        with patch("app.services.providers.campay.CampayClient.disburse") as disburse:
            updated, ok, message = _attempt_council_credit(db, txn)
            assert ok is False
            assert "debit not confirmed" in message.lower()
            disburse.assert_not_called()
    finally:
        db.close()


def test_utility_provider_blocked_before_debit_confirmed(client):
    _ensure_utilities()
    token = _login(client, "abctrading", "payer123")
    headers = {"Authorization": f"Bearer {token}"}
    store = client.get("/api/v1/utility-services/store", headers=headers).json()
    svc = next(s for s in store if s["code"] == "ENEO")

    from app.services.providers.campay import CampayClient, CampayResult

    real_init = CampayClient.__init__

    def init_live(self, db):
        real_init(self, db)
        self.mock = False  # PENDING must not auto-confirm as SUCCESS

    pending = CampayResult(ok=True, reference="pending-ref", status="PENDING", raw={"status": "PENDING"})

    # Patch status poll to PENDING so debit is not confirmed; provider must not run
    with patch.object(CampayClient, "__init__", init_live), patch.object(
        CampayClient, "collect", return_value=pending
    ), patch.object(CampayClient, "get_transaction_status", return_value=pending), patch(
        "app.services.providers.utility_bill.UtilityBillClient.pay_bill"
    ) as pay_bill:
        pay = client.post(
            "/api/v1/utility-payments/initiate",
            headers=headers,
            json={
                "utility_service_id": svc["utility_service_id"],
                "amount": 5000,
                "meter_number": "ENEO-M-100",
                "phone_number": "670000001",
                "idempotency_key": f"debit-guard-utl-{__import__('uuid').uuid4().hex[:12]}",
            },
        )
        assert pay.status_code == 200, pay.text
        body = pay.json()
        assert body["status"] == "PROCESSING"
        assert body["ok"] is False
        pay_bill.assert_not_called()

        db = SessionLocal()
        try:
            txn = db.get(Transaction, body["transaction_id"])
            assert txn.status == "PROCESSING"
            intents = (
                db.query(ProviderPaymentIntent)
                .filter(
                    ProviderPaymentIntent.entity_id == txn.transaction_id,
                    ProviderPaymentIntent.operation == "UTILITY_PAY",
                )
                .all()
            )
            assert intents == []
            _, ok, message = _attempt_utility_provider_credit(db, txn)
            assert ok is False
            assert "debit not confirmed" in message.lower()
        finally:
            db.close()


def test_utility_provider_runs_only_after_debit_success(client):
    _ensure_utilities()
    token = _login(client, "abctrading", "payer123")
    headers = {"Authorization": f"Bearer {token}"}
    store = client.get("/api/v1/utility-services/store", headers=headers).json()
    svc = next(s for s in store if s["code"] == "CAMWATER")
    pay = client.post(
        "/api/v1/utility-payments/initiate",
        headers=headers,
        json={
            "utility_service_id": svc["utility_service_id"],
            "amount": 4200,
            "bill_number": "CW-BILL-55",
            "phone_number": "670000001",
            "idempotency_key": f"debit-ok-utl-{__import__('uuid').uuid4().hex[:12]}",
        },
    )
    assert pay.status_code == 200, pay.text
    body = pay.json()
    assert body["status"] == "SETTLED"
    assert body["ok"] is True

    db = SessionLocal()
    try:
        txn = db.get(Transaction, body["transaction_id"])
        assert txn.failure_stage is None or txn.failure_stage == ""
        collect = (
            db.query(ProviderPaymentIntent)
            .filter(
                ProviderPaymentIntent.entity_id == txn.transaction_id,
                ProviderPaymentIntent.operation == "COLLECT",
            )
            .first()
        )
        utility_pay = (
            db.query(ProviderPaymentIntent)
            .filter(
                ProviderPaymentIntent.entity_id == txn.transaction_id,
                ProviderPaymentIntent.operation == "UTILITY_PAY",
            )
            .first()
        )
        assert collect is not None
        assert utility_pay is not None
        assert collect.created_at <= utility_pay.created_at
        assert txn.credit_payout_method == "UTILITY"
        assert txn.credit_provider_reference
    finally:
        db.close()


def test_confirm_payer_debit_helper_sets_debited(client):
    token = _login(client, "abctrading", "payer123")
    headers = {"Authorization": f"Bearer {token}"}
    due = client.get("/api/v1/obligations?status=DUE", headers=headers)
    items = due.json() if isinstance(due.json(), list) else due.json().get("items") or []
    obl = items[0]
    init = client.post(
        "/api/v1/payments/initiate",
        headers=headers,
        json={
            "obligation_id": obl["obligation_id"],
            "payment_channel": "MOBILE_MONEY",
            "phone_number": "670000001",
            "idempotency_key": f"confirm-debit-{__import__('uuid').uuid4().hex[:12]}",
        },
    )
    assert init.status_code == 200, init.text
    db = SessionLocal()
    try:
        txn = db.get(Transaction, init.json()["transaction_id"])
        if txn.status == "FAILED":
            return  # collect declined in this env — skip
        updated, ok = confirm_payer_debit(db, txn)
        assert ok is True
        assert updated.status == "DEBITED"
    finally:
        db.close()
