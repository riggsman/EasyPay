from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.base import new_id, utcnow
from app.models.geography import GeographicUnit
from app.models.ledger import FinancialAccount, LedgerEntry, LedgerPosting
from app.models.obligation import Obligation
from app.models.payer import Payer
from app.models.receipt import Receipt
from app.models.revenue import RevenueType
from app.models.tenant import Tenant
from app.models.transaction import Collection, IdempotencyKey, Transaction, TransactionEvent
from app.schemas.common import PaymentInitiateRequest, PaymentResolveRequest, PaymentResolveResponse
from app.services.audit import write_audit
from app.services.fees import calculate_commission, calculate_fee


# Terminal outcomes share one stage: SETTLED (success) or FAILED (failure).
# MANUAL_INTERVENTION is ops-resolvable after credit retries are exhausted.
# REJECTED remains accepted as a legacy alias for FAILED.
VALID_TRANSITIONS = {
    "INITIATED": {"PROCESSING", "FAILED", "REJECTED"},
    "PROCESSING": {"DEBITED", "FAILED", "REJECTED"},
    "DEBITED": {"CREDITED", "FAILED", "REJECTED"},
    "CREDITED": {"SETTLED", "FAILED", "REJECTED"},
    "FAILED": {"CREDITED", "MANUAL_INTERVENTION"},
    "MANUAL_INTERVENTION": {"CREDITED", "SETTLED"},
    "SETTLED": set(),
    "REJECTED": {"CREDITED", "MANUAL_INTERVENTION"},
}

TERMINAL_STATUSES = frozenset({"SETTLED"})
DEFAULT_CREDIT_MAX_RETRIES = 3
CONFIG_CREDIT_MAX_RETRIES = "payments.credit.max_retries"

# Stable UI order when several events share the same timestamp.
# FAILED / MANUAL_INTERVENTION sit at the same terminal stage as SETTLED.
TIMELINE_STATUS_ORDER = {
    "INITIATED": 0,
    "PROCESSING": 1,
    "DEBITED": 2,
    "CREDITED": 3,
    "SETTLED": 4,
    "FAILED": 4,
    "MANUAL_INTERVENTION": 4,
    "REJECTED": 4,
}

TIMELINE_LABELS = {
    "INITIATED": "Initiated",
    "PROCESSING": "Payment processing",
    "DEBITED": "Customer account debited",
    "CREDITED": "Council credited",
    "SETTLED": "Settlement completed",
    "FAILED": "Payment failed",
    "MANUAL_INTERVENTION": "Manual intervention required",
    "REJECTED": "Payment failed",
}

# Role-scoped intermediary visibility: payers see debit; council sees credit; platform sees all
_PAYER_TIMELINE_STATUSES = frozenset(
    {"INITIATED", "PROCESSING", "DEBITED", "SETTLED", "FAILED", "REJECTED", "MANUAL_INTERVENTION"}
)
_COUNCIL_TIMELINE_STATUSES = frozenset(
    {"INITIATED", "PROCESSING", "CREDITED", "SETTLED", "FAILED", "REJECTED", "MANUAL_INTERVENTION"}
)
_PLATFORM_USER_TYPES = frozenset({"PLATFORM_ADMIN", "SUPER_ADMIN"})


def normalize_transaction_status(status: str) -> str:
    """Map legacy REJECTED onto FAILED (terminal failure)."""
    return "FAILED" if status == "REJECTED" else status


def timeline_visible_statuses(user_type: Optional[str]) -> Optional[frozenset]:
    """Return allowed to_status values, or None when the audience sees every state."""
    if not user_type or user_type in _PLATFORM_USER_TYPES:
        return None
    if user_type == "PAYER":
        return _PAYER_TIMELINE_STATUSES
    return _COUNCIL_TIMELINE_STATUSES


def timeline_label(to_status: str) -> str:
    return TIMELINE_LABELS.get(to_status, to_status.replace("_", " ").title())


def serialize_timeline_event(event: TransactionEvent, *, user_type: Optional[str] = None) -> dict:
    """Audience-aware event payload: ordered labels, no provider noise for non-platform users."""
    label = timeline_label(event.to_status)
    note = (event.note or "").strip()
    if user_type not in _PLATFORM_USER_TYPES:
        lower = note.lower()
        if lower.startswith("campay ") or lower.startswith("provider "):
            note = label
        elif not note:
            note = label
    elif not note:
        note = label
    return {
        "from_status": event.from_status,
        "to_status": event.to_status,
        "label": label,
        "note": note,
        "created_at": event.created_at,
    }


def credit_max_retries(db: Session) -> int:
    from app.models.config import SystemConfiguration

    row = (
        db.query(SystemConfiguration)
        .filter(SystemConfiguration.config_key == CONFIG_CREDIT_MAX_RETRIES, SystemConfiguration.tenant_id.is_(None))
        .first()
    )
    if not row or row.config_value is None:
        return DEFAULT_CREDIT_MAX_RETRIES
    try:
        value = int(str(row.config_value).strip())
        return max(0, value)
    except ValueError:
        return DEFAULT_CREDIT_MAX_RETRIES


def ensure_credit_retry_settings(db: Session) -> None:
    from app.services.history_exports import upsert_platform_config

    upsert_platform_config(
        db,
        CONFIG_CREDIT_MAX_RETRIES,
        str(DEFAULT_CREDIT_MAX_RETRIES),
        "Max automatic council-credit retries before MANUAL_INTERVENTION",
    )


def net_credit_amount(txn: Transaction) -> Decimal:
    return Decimal(str(txn.amount)) - Decimal(str(txn.commission_amount or 0))


def build_manual_credit_context(db: Session, txn: Transaction) -> dict:
    tenant = db.get(Tenant, txn.transaction_tenant_id)
    method = (txn.credit_payout_method or "MOMO").upper()
    if method == "MOBILE_MONEY":
        method = "MOMO"
    momo = txn.credit_destination if method == "MOMO" else None
    bank = txn.credit_destination if method == "BANK" else None
    if tenant:
        momo = momo or tenant.momo_number
        bank = bank or tenant.bank_account_number
    max_retries = credit_max_retries(db)
    return {
        "transaction_id": txn.transaction_id,
        "transaction_reference": txn.transaction_reference,
        "status": txn.status,
        "failure_reason": txn.failure_reason,
        "failure_stage": txn.failure_stage,
        "credit_retry_count": txn.credit_retry_count or 0,
        "max_credit_retries": max_retries,
        "retries_remaining": max(0, max_retries - (txn.credit_retry_count or 0)),
        "can_retry": txn.status in ("FAILED", "REJECTED")
        and (txn.failure_stage or "CREDIT") == "CREDIT"
        and (txn.credit_retry_count or 0) < max_retries,
        "needs_manual_intervention": txn.status == "MANUAL_INTERVENTION"
        or (
            txn.status in ("FAILED", "REJECTED")
            and (txn.failure_stage or "CREDIT") == "CREDIT"
            and (txn.credit_retry_count or 0) >= max_retries
        ),
        "tenant_id": txn.transaction_tenant_id,
        "council_name": tenant.organization_name if tenant else None,
        "council_email": tenant.email if tenant else None,
        "council_phone": tenant.phone_number if tenant else None,
        "amount": str(txn.amount),
        "commission_amount": str(txn.commission_amount or 0),
        "net_credit_amount": str(net_credit_amount(txn)),
        "currency": txn.currency or "XAF",
        "payout_method": method if method in ("MOMO", "BANK") else "MOMO",
        "momo_number": momo,
        "bank_account_number": bank,
        "bank_account_name": tenant.organization_name if tenant else None,
        "bank_code": "CM_DEFAULT",
        "warnings": [
            "This credits the council outside the automatic Campay path.",
            "Confirm destination details before proceeding — incorrect payouts may be irreversible.",
            "Ledger settlement will complete only after a successful manual credit.",
        ],
    }


def _next_ref(db: Session, prefix: str) -> str:
    # Simple sequential reference
    year = utcnow().year
    if prefix == "TXN":
        n = db.query(Transaction).count() + 1
    elif prefix == "RCPT":
        n = db.query(Receipt).count() + 1
    else:
        n = 1
    return f"{prefix}-{year}-{n:07d}"


def resolve_payment_context(db: Session, payer: Payer, data: PaymentResolveRequest) -> PaymentResolveResponse:
    if not payer.current_geographic_unit_id or not payer.tenant_id:
        raise HTTPException(status_code=422, detail="Payer has no active operating zone")

    obligation = db.get(Obligation, data.obligation_id)
    if not obligation or obligation.status in ("CANCELLED", "WAIVED"):
        raise HTTPException(status_code=404, detail="Obligation not found")

    # Backend must independently verify payer + zone + tenant + obligation
    if obligation.payer_id != payer.payer_id:
        raise HTTPException(status_code=403, detail="Obligation does not belong to this payer")
    if obligation.tenant_id != payer.tenant_id:
        raise HTTPException(status_code=403, detail="ZONE_MISMATCH: obligation tenant does not match payer zone")
    if obligation.geographic_unit_id != payer.current_geographic_unit_id:
        raise HTTPException(
            status_code=403,
            detail="ZONE_MISMATCH: obligation zone does not match payer current operating area",
        )
    if obligation.balance <= 0 or obligation.status == "PAID":
        raise HTTPException(status_code=422, detail="Obligation has no outstanding balance")

    geo = db.get(GeographicUnit, obligation.geographic_unit_id)
    tenant = db.get(Tenant, obligation.tenant_id)
    revenue = db.get(RevenueType, obligation.revenue_type_id)

    amount = obligation.balance
    fee = calculate_fee(
        db,
        amount=amount,
        tenant_id=obligation.tenant_id,
        geographic_unit_id=obligation.geographic_unit_id,
        revenue_type_id=obligation.revenue_type_id,
        payment_channel_code=data.payment_channel,
    )
    commission = calculate_commission(
        db, amount=amount, tenant_id=obligation.tenant_id, revenue_type_id=obligation.revenue_type_id
    )

    return PaymentResolveResponse(
        payer_id=payer.payer_id,
        obligation_id=obligation.obligation_id,
        tenant_id=obligation.tenant_id,
        geographic_unit_id=obligation.geographic_unit_id,
        council_name=tenant.organization_name if tenant else "",
        operating_area=geo.unit_name if geo else "",
        revenue_type_id=obligation.revenue_type_id,
        revenue_name=revenue.name if revenue else "",
        amount=amount,
        service_fee=fee,
        commission_amount=commission,
        total_amount=amount + fee,
        currency=obligation.currency,
        payment_channel=data.payment_channel,
    )


def initiate_payment(db: Session, payer: Payer, data: PaymentInitiateRequest, actor_user_id: str) -> Transaction:
    existing = db.query(IdempotencyKey).filter(IdempotencyKey.key_value == data.idempotency_key, IdempotencyKey.scope == "payment").first()
    if existing and existing.response_ref:
        txn = db.get(Transaction, existing.response_ref)
        if txn:
            return txn

    ctx = resolve_payment_context(
        db, payer, PaymentResolveRequest(obligation_id=data.obligation_id, payment_channel=data.payment_channel)
    )

    collection = Collection(
        payer_id=payer.payer_id,
        tenant_id=ctx.tenant_id,
        geographic_unit_id=ctx.geographic_unit_id,
        obligation_id=ctx.obligation_id,
        amount=ctx.amount,
        currency=ctx.currency,
        status="OPEN",
    )
    db.add(collection)
    db.flush()

    channel = (data.payment_channel or "MOBILE_MONEY").upper()
    is_momo = channel in ("MOBILE_MONEY", "MOMO", "MTN_MOMO", "ORANGE_MONEY")
    phone = data.phone_number or payer.phone_number
    if is_momo and not phone:
        raise HTTPException(status_code=422, detail="phone_number required for Mobile Money payments")

    txn = Transaction(
        transaction_reference=_next_ref(db, "TXN"),
        correlation_id=new_id("cor_"),
        idempotency_key=data.idempotency_key,
        payer_id=payer.payer_id,
        transaction_tenant_id=ctx.tenant_id,
        transaction_geographic_unit_id=ctx.geographic_unit_id,
        obligation_id=ctx.obligation_id,
        revenue_type_id=ctx.revenue_type_id,
        collection_id=collection.collection_id,
        amount=ctx.amount,
        service_fee=ctx.service_fee,
        commission_amount=ctx.commission_amount,
        total_amount=ctx.total_amount,
        currency=ctx.currency,
        payment_channel="MOBILE_MONEY" if is_momo else channel,
        payment_provider="CAMPAY" if is_momo else None,
        payer_msisdn=phone if is_momo else None,
        status="INITIATED",
        initiated_at=utcnow(),
    )
    db.add(txn)
    db.flush()
    _add_event(db, txn, None, "INITIATED", "Payment initiated", actor_user_id)

    if is_momo:
        from app.services.providers.campay import CampayClient, record_intent

        client = CampayClient(db)
        result = client.collect(
            amount=txn.total_amount,
            phone=phone,
            description=f"EasyPay {txn.transaction_reference}",
            external_reference=txn.transaction_reference,
            currency=txn.currency,
        )
        record_intent(
            db,
            operation="COLLECT",
            entity_type="transaction",
            entity_id=txn.transaction_id,
            tenant_id=txn.transaction_tenant_id,
            amount=str(txn.total_amount),
            currency=txn.currency,
            destination=phone,
            result=result,
            external_reference=txn.transaction_reference,
            payout_method="MOMO",
        )
        txn.provider_reference = result.reference
        txn.provider_status = result.status
        if not result.ok:
            txn.status = "FAILED"
            txn.failure_stage = "DEBIT"
            txn.failure_reason = result.error or "Payer debit failed"
            _add_event(db, txn, "INITIATED", "FAILED", txn.failure_reason, actor_user_id)
        else:
            txn.status = "PROCESSING"
            # Keep provider reference on the transaction; timeline note stays human-readable
            _add_event(db, txn, "INITIATED", "PROCESSING", "Payment processing", actor_user_id)

    db.add(IdempotencyKey(key_value=data.idempotency_key, scope="payment", response_ref=txn.transaction_id))
    write_audit(
        db,
        actor_user_id=actor_user_id,
        tenant_id=ctx.tenant_id,
        entity_type="transaction",
        entity_id=txn.transaction_id,
        action="INITIATE",
        after={
            "amount": str(ctx.amount),
            "zone": ctx.geographic_unit_id,
            "provider": txn.payment_provider,
            "provider_reference": txn.provider_reference,
        },
    )
    db.commit()
    db.refresh(txn)
    from app.realtime.publisher import publish_transaction_status

    publish_transaction_status(
        db,
        txn,
        from_status=None,
        to_status=txn.status,
        note="Payment initiated via Campay" if is_momo else "Payment initiated",
        actor_user_id=actor_user_id,
    )
    return txn


def advance_transaction(db: Session, txn: Transaction, to_status: str, actor_user_id: Optional[str] = None, note: str = "") -> Transaction:
    to_status = to_status if to_status == "MANUAL_INTERVENTION" else normalize_transaction_status(to_status)
    current = normalize_transaction_status(txn.status) if txn.status != "MANUAL_INTERVENTION" else txn.status
    if current == "SETTLED":
        if to_status == current:
            return txn
        raise HTTPException(status_code=422, detail=f"Cannot transition from terminal status {txn.status}")
    allowed = VALID_TRANSITIONS.get(txn.status, set()) | VALID_TRANSITIONS.get(current, set())
    allowed_norm = {normalize_transaction_status(s) if s != "MANUAL_INTERVENTION" else s for s in allowed}
    if to_status not in allowed and to_status not in allowed_norm:
        raise HTTPException(status_code=422, detail=f"Cannot transition from {txn.status} to {to_status}")
    from_status = txn.status
    default_note = {
        "FAILED": "Payment failed",
        "MANUAL_INTERVENTION": "Manual intervention required",
        "CREDITED": "Council credited",
        "SETTLED": "Settlement completed",
    }.get(to_status, "")
    _add_event(db, txn, from_status, to_status, note or default_note, actor_user_id)
    txn.status = to_status
    if to_status == "SETTLED":
        txn.settled_at = utcnow()
        txn.failure_reason = None
        txn.failure_stage = None
        _post_ledger(db, txn)
        _update_obligation(db, txn)
        _issue_receipt(db, txn)
        from app.services.notifications.dispatcher import notify_payment_settled

        notify_payment_settled(db, txn)
        if txn.collection_id:
            col = db.get(Collection, txn.collection_id)
            if col:
                col.status = "COMPLETED"
    elif to_status == "CREDITED":
        txn.failure_reason = None
        txn.failure_stage = None
    elif to_status == "FAILED" and txn.collection_id:
        col = db.get(Collection, txn.collection_id)
        if col and col.status not in ("COMPLETED",):
            col.status = "FAILED"
    elif to_status == "MANUAL_INTERVENTION":
        txn.manual_intervention_at = utcnow()
        if actor_user_id:
            txn.manual_intervention_by = actor_user_id
    db.commit()
    db.refresh(txn)
    from app.realtime.publisher import publish_transaction_status

    publish_transaction_status(
        db,
        txn,
        from_status=from_status,
        to_status=to_status,
        note=note,
        actor_user_id=actor_user_id,
    )
    return txn


def _mark_credit_failure(db: Session, txn: Transaction, reason: str, actor_user_id: Optional[str] = None) -> Transaction:
    txn.failure_reason = reason
    txn.failure_stage = "CREDIT"
    db.flush()
    if txn.status in ("FAILED", "REJECTED"):
        _add_event(db, txn, txn.status, "FAILED", reason, actor_user_id)
        db.commit()
        db.refresh(txn)
        return txn
    return advance_transaction(db, txn, "FAILED", actor_user_id, reason)


def _attempt_council_credit(
    db: Session,
    txn: Transaction,
    *,
    actor_user_id: Optional[str] = None,
    payout_method: Optional[str] = None,
    momo_number: Optional[str] = None,
    bank_account_number: Optional[str] = None,
    bank_account_name: Optional[str] = None,
    bank_code: Optional[str] = None,
    force_fail_reason: Optional[str] = None,
) -> tuple[Transaction, bool, str]:
    """Disburse net amount to council. Returns (txn, ok, message)."""
    from app.services.providers.campay import CampayClient, record_intent

    tenant = db.get(Tenant, txn.transaction_tenant_id)
    if not tenant:
        return txn, False, "Council tenant not found for credit"

    method = (payout_method or txn.credit_payout_method or "MOMO").upper()
    if method == "MOBILE_MONEY":
        method = "MOMO"
    if method not in ("MOMO", "BANK"):
        return txn, False, "payout_method must be MOMO or BANK"

    amount = net_credit_amount(txn)
    if amount <= 0:
        return txn, False, "Net credit amount must be greater than zero"

    external_ref = f"{txn.transaction_reference}-CREDIT-{(txn.credit_retry_count or 0) + 1}"
    client = CampayClient(db)

    if force_fail_reason:
        txn.credit_payout_method = method
        txn.credit_destination = momo_number or bank_account_number or txn.credit_destination
        return txn, False, force_fail_reason

    if method == "MOMO":
        phone = momo_number or txn.credit_destination or tenant.momo_number
        if not phone:
            return txn, False, "Council MoMo number is missing — cannot credit council"
        # Simulation hook: destinations containing FAIL force a credit failure
        if "FAIL" in phone.upper() or phone.replace(" ", "").endswith("000000"):
            txn.credit_payout_method = "MOMO"
            txn.credit_destination = phone
            return txn, False, (
                f"Council credit failed: destination {phone} rejected by payout provider "
                "(simulated unavailable float / invalid MoMo account)"
            )
        result = client.disburse(
            amount=amount,
            phone=phone,
            description=f"Council credit {txn.transaction_reference}",
            external_reference=external_ref,
            currency=txn.currency or "XAF",
        )
        record_intent(
            db,
            operation="DISBURSE",
            entity_type="transaction",
            entity_id=txn.transaction_id,
            tenant_id=txn.transaction_tenant_id,
            amount=str(amount),
            currency=txn.currency or "XAF",
            destination=phone,
            result=result,
            external_reference=external_ref,
            payout_method="MOMO",
        )
        txn.credit_payout_method = "MOMO"
        txn.credit_destination = phone
        txn.credit_provider_reference = result.reference
        if not result.ok:
            return txn, False, result.error or "Campay MoMo council credit failed"
        return txn, True, "Council credited via MoMo"
    else:
        account = bank_account_number or txn.credit_destination or tenant.bank_account_number
        account_name = bank_account_name or tenant.organization_name or "Council"
        code = bank_code or "CM_DEFAULT"
        if not account:
            return txn, False, "Council bank account is missing — cannot credit council"
        if "FAIL" in account.upper():
            txn.credit_payout_method = "BANK"
            txn.credit_destination = account
            return txn, False, (
                f"Council credit failed: bank account {account} rejected by payout provider "
                "(simulated bank transfer failure)"
            )
        result = client.bank_transfer(
            amount=amount,
            account_number=account,
            account_name=account_name,
            bank_code=code,
            description=f"Council credit {txn.transaction_reference}",
            external_reference=external_ref,
            currency=txn.currency or "XAF",
        )
        record_intent(
            db,
            operation="BANK_TRANSFER",
            entity_type="transaction",
            entity_id=txn.transaction_id,
            tenant_id=txn.transaction_tenant_id,
            amount=str(amount),
            currency=txn.currency or "XAF",
            destination=account,
            result=result,
            external_reference=external_ref,
            payout_method="BANK",
        )
        txn.credit_payout_method = "BANK"
        txn.credit_destination = account
        txn.credit_provider_reference = result.reference
        if not result.ok:
            return txn, False, result.error or "Campay bank council credit failed"
        return txn, True, "Council credited via bank transfer"


def retry_council_credit(db: Session, transaction_id: str, actor_user_id: Optional[str] = None) -> Transaction:
    txn = db.get(Transaction, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    ctx = build_manual_credit_context(db, txn)
    if txn.status == "MANUAL_INTERVENTION":
        raise HTTPException(status_code=422, detail="Retries exhausted — use manual intervention")
    if not ctx["can_retry"]:
        raise HTTPException(status_code=422, detail="Transaction is not eligible for credit retry")
    txn.credit_retry_count = (txn.credit_retry_count or 0) + 1
    db.flush()
    txn, ok, message = _attempt_council_credit(db, txn, actor_user_id=actor_user_id)
    if ok:
        txn = advance_transaction(db, txn, "CREDITED", actor_user_id, message)
        return advance_transaction(db, txn, "SETTLED", actor_user_id, "Settlement completed")
    txn = _mark_credit_failure(db, txn, message, actor_user_id)
    if (txn.credit_retry_count or 0) >= credit_max_retries(db):
        txn = advance_transaction(
            db,
            txn,
            "MANUAL_INTERVENTION",
            actor_user_id,
            f"Credit retries exhausted ({txn.credit_retry_count}/{credit_max_retries(db)}). {message}",
        )
    return txn


def manual_council_credit(
    db: Session,
    transaction_id: str,
    *,
    actor_user_id: str,
    confirm: bool,
    payout_method: str = "MOMO",
    momo_number: Optional[str] = None,
    bank_account_number: Optional[str] = None,
    bank_account_name: Optional[str] = None,
    bank_code: Optional[str] = None,
    amount: Optional[Decimal] = None,
) -> Transaction:
    if not confirm:
        raise HTTPException(status_code=422, detail="Confirmation required to proceed with manual credit")
    txn = db.get(Transaction, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if txn.status not in ("MANUAL_INTERVENTION", "FAILED", "REJECTED"):
        raise HTTPException(status_code=422, detail="Manual credit only allowed for failed / intervention transactions")
    if txn.failure_stage and txn.failure_stage != "CREDIT" and txn.status != "MANUAL_INTERVENTION":
        raise HTTPException(status_code=422, detail="Manual council credit applies to CREDIT-stage failures")

    expected = net_credit_amount(txn)
    if amount is not None and Decimal(str(amount)) != expected:
        # Allow edit but warn via audit; still use provided amount for payout
        pass
    payout_amount = Decimal(str(amount)) if amount is not None else expected
    if payout_amount != expected:
        # Temporarily adjust commission so net matches operator override for this payout only
        # Keep original amount; store override in note
        override_note = f"Manual amount override {payout_amount} (default net {expected})"
    else:
        override_note = None

    # If operator changed net, run payout with that amount by briefly swapping commission math
    original_commission = txn.commission_amount
    if payout_amount != expected:
        txn.commission_amount = Decimal(str(txn.amount)) - payout_amount
        db.flush()

    try:
        txn, ok, message = _attempt_council_credit(
            db,
            txn,
            actor_user_id=actor_user_id,
            payout_method=payout_method,
            momo_number=momo_number,
            bank_account_number=bank_account_number,
            bank_account_name=bank_account_name,
            bank_code=bank_code,
        )
    finally:
        if payout_amount != expected:
            txn.commission_amount = original_commission
            db.flush()

    write_audit(
        db,
        actor_user_id=actor_user_id,
        tenant_id=txn.transaction_tenant_id,
        entity_type="transaction",
        entity_id=txn.transaction_id,
        action="MANUAL_CREDIT",
        reason=override_note or message,
        after={
            "payout_method": payout_method,
            "momo_number": momo_number,
            "bank_account_number": bank_account_number,
            "amount": str(payout_amount),
            "ok": ok,
            "message": message,
        },
    )
    if not ok:
        txn.failure_reason = message
        txn.failure_stage = "CREDIT"
        db.commit()
        db.refresh(txn)
        raise HTTPException(status_code=502, detail=message)

    if txn.status != "CREDITED":
        txn = advance_transaction(
            db,
            txn,
            "CREDITED",
            actor_user_id,
            f"Manual council credit successful. {message}",
        )
    return advance_transaction(db, txn, "SETTLED", actor_user_id, "Settlement completed after manual credit")


def complete_payment_happy_path(db: Session, transaction_id: str, actor_user_id: Optional[str] = None) -> Transaction:
    txn = db.get(Transaction, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if txn.status in ("SETTLED", "FAILED", "REJECTED", "MANUAL_INTERVENTION"):
        return txn

    # MoMo must settle only after Campay confirms SUCCESSFUL
    if txn.payment_provider == "CAMPAY" and txn.provider_reference:
        from app.services.providers.campay import CampayClient

        client = CampayClient(db)
        status_result = client.get_transaction_status(txn.provider_reference)
        txn.provider_status = status_result.status
        db.flush()
        if status_result.status in ("FAILED", "CANCELED", "CANCELLED"):
            txn.failure_stage = "DEBIT"
            txn.failure_reason = f"Payer debit failed ({status_result.status})"
            if normalize_transaction_status(txn.status) != "FAILED":
                txn = advance_transaction(
                    db,
                    txn,
                    "FAILED",
                    actor_user_id,
                    txn.failure_reason,
                )
            return txn
        if status_result.status not in ("SUCCESSFUL", "SUCCESS", "COMPLETED") and not client.mock:
            # Leave in PROCESSING until webhook/poll confirms
            db.commit()
            db.refresh(txn)
            return txn

    for state, note in [
        ("PROCESSING", "Payment processing"),
        ("DEBITED", "Customer account debited via Campay" if txn.payment_provider == "CAMPAY" else "Customer account debited"),
    ]:
        if txn.status in ("FAILED", "REJECTED", "MANUAL_INTERVENTION"):
            return txn
        if txn.status != state:
            txn = advance_transaction(db, txn, state, actor_user_id, note)

    if txn.status == "DEBITED":
        # Force-fail hook for demo keys
        force = None
        if (txn.idempotency_key or "").startswith("sim-credit-fail"):
            force = (
                "Council credit failed: payout provider returned insufficient float "
                "for destination account (simulated)"
            )
        txn, ok, message = _attempt_council_credit(db, txn, actor_user_id=actor_user_id, force_fail_reason=force)
        if not ok:
            return _mark_credit_failure(db, txn, message, actor_user_id)
        txn = advance_transaction(db, txn, "CREDITED", actor_user_id, message)

    if txn.status == "CREDITED":
        txn = advance_transaction(db, txn, "SETTLED", actor_user_id, "Settlement completed")
    return txn


def _add_event(db: Session, txn: Transaction, from_status: Optional[str], to_status: str, note: str, actor: Optional[str]) -> None:
    db.add(
        TransactionEvent(
            transaction_id=txn.transaction_id,
            from_status=from_status,
            to_status=to_status,
            note=note,
            actor_user_id=actor,
        )
    )


def _ensure_accounts(db: Session, tenant_id: str) -> dict:
    codes = {
        "CASH": ("Cash / MoMo Clearing", "ASSET"),
        "PAYABLE": ("Tenant Settlement Payable", "LIABILITY"),
        "FEE_REV": ("Platform Service Fee Revenue", "REVENUE"),
        "COMM_REV": ("Platform Commission Revenue", "REVENUE"),
    }
    out = {}
    for code, (name, atype) in codes.items():
        acct = (
            db.query(FinancialAccount)
            .filter(FinancialAccount.tenant_id == tenant_id, FinancialAccount.account_code == code)
            .first()
        )
        if not acct:
            acct = FinancialAccount(
                tenant_id=tenant_id,
                account_code=code,
                account_name=name,
                account_type=atype,
            )
            db.add(acct)
            db.flush()
        out[code] = acct
    return out


def _post_ledger(db: Session, txn: Transaction) -> None:
    accounts = _ensure_accounts(db, txn.transaction_tenant_id)
    posting = LedgerPosting(
        transaction_id=txn.transaction_id,
        tenant_id=txn.transaction_tenant_id,
        geographic_unit_id=txn.transaction_geographic_unit_id,
        description=f"Payment {txn.transaction_reference}",
        posting_type="PAYMENT",
    )
    db.add(posting)
    db.flush()

    # Debit cash for total; credit payable for net to tenant; credit fee & commission revenues
    net_to_tenant = txn.amount - txn.commission_amount
    entries = [
        (accounts["CASH"], txn.total_amount, Decimal("0"), "Customer payment received"),
        (accounts["PAYABLE"], Decimal("0"), net_to_tenant, "Amount due to council"),
        (accounts["FEE_REV"], Decimal("0"), txn.service_fee, "Service fee"),
        (accounts["COMM_REV"], Decimal("0"), txn.commission_amount, "Commission"),
    ]
    total_d = sum(e[1] for e in entries)
    total_c = sum(e[2] for e in entries)
    if total_d != total_c:
        raise HTTPException(status_code=500, detail=f"Unbalanced ledger posting: {total_d} != {total_c}")

    for acct, debit, credit, narrative in entries:
        if debit == 0 and credit == 0:
            continue
        db.add(
            LedgerEntry(
                ledger_posting_id=posting.ledger_posting_id,
                financial_account_id=acct.financial_account_id,
                tenant_id=txn.transaction_tenant_id,
                geographic_unit_id=txn.transaction_geographic_unit_id,
                debit=debit,
                credit=credit,
                currency=txn.currency,
                narrative=narrative,
            )
        )


def _update_obligation(db: Session, txn: Transaction) -> None:
    if not txn.obligation_id:
        return
    obl = db.get(Obligation, txn.obligation_id)
    if not obl:
        return
    obl.balance = max(Decimal("0"), obl.balance - txn.amount)
    if obl.balance == 0:
        obl.status = "PAID"
    else:
        obl.status = "PARTIAL"


def _issue_receipt(db: Session, txn: Transaction) -> Receipt:
    existing = db.query(Receipt).filter(Receipt.transaction_id == txn.transaction_id).first()
    if existing:
        return existing
    payer = db.get(Payer, txn.payer_id)
    tenant = db.get(Tenant, txn.transaction_tenant_id)
    revenue = db.get(RevenueType, txn.revenue_type_id) if txn.revenue_type_id else None
    receipt = Receipt(
        receipt_number=_next_ref(db, "RCPT"),
        verification_token=new_id("v_"),
        transaction_id=txn.transaction_id,
        payer_id=txn.payer_id,
        tenant_id=txn.transaction_tenant_id,
        geographic_unit_id=txn.transaction_geographic_unit_id,
        revenue_type_id=txn.revenue_type_id,
        payer_display_name=(payer.business_name or payer.full_name) if payer else "Payer",
        council_name=tenant.organization_name if tenant else "Council",
        revenue_name=revenue.name if revenue else None,
        amount=txn.amount,
        service_fee=txn.service_fee,
        total_amount=txn.total_amount,
        currency=txn.currency,
        payment_date=txn.settled_at or utcnow(),
        payment_channel=txn.payment_channel,
        status="ISSUED",
    )
    db.add(receipt)
    return receipt


def get_transaction_events(
    db: Session,
    transaction_id: str,
    user_type: Optional[str] = None,
) -> List[TransactionEvent]:
    """Return timeline events in machine order, filtered for the viewer's role."""
    events = (
        db.query(TransactionEvent)
        .filter(TransactionEvent.transaction_id == transaction_id)
        .all()
    )
    events.sort(
        key=lambda e: (
            e.created_at or utcnow(),
            TIMELINE_STATUS_ORDER.get(e.to_status, 99),
            e.transaction_event_id or "",
        )
    )
    visible = timeline_visible_statuses(user_type)
    if visible is not None:
        events = [e for e in events if e.to_status in visible]
    return events
