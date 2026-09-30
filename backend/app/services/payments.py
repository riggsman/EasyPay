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


VALID_TRANSITIONS = {
    "INITIATED": {"PROCESSING", "REJECTED"},
    "PROCESSING": {"DEBITED", "REJECTED"},
    "DEBITED": {"CREDITED", "REJECTED"},
    "CREDITED": {"SETTLED"},
    "SETTLED": set(),
    "REJECTED": set(),
}

# Stable UI order when several events share the same timestamp
TIMELINE_STATUS_ORDER = {
    "INITIATED": 0,
    "PROCESSING": 1,
    "DEBITED": 2,
    "CREDITED": 3,
    "SETTLED": 4,
    "REJECTED": 5,
}

TIMELINE_LABELS = {
    "INITIATED": "Initiated",
    "PROCESSING": "Payment processing",
    "DEBITED": "Customer account debited",
    "CREDITED": "Council credited",
    "SETTLED": "Settlement completed",
    "REJECTED": "Rejected",
}

# Role-scoped intermediary visibility: payers see debit; council sees credit; platform sees all
_PAYER_TIMELINE_STATUSES = frozenset({"INITIATED", "PROCESSING", "DEBITED", "SETTLED", "REJECTED"})
_COUNCIL_TIMELINE_STATUSES = frozenset({"INITIATED", "PROCESSING", "CREDITED", "SETTLED", "REJECTED"})
_PLATFORM_USER_TYPES = frozenset({"PLATFORM_ADMIN", "SUPER_ADMIN"})


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
            txn.status = "REJECTED"
            _add_event(db, txn, "INITIATED", "REJECTED", result.error or "Campay collect failed", actor_user_id)
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
    allowed = VALID_TRANSITIONS.get(txn.status, set())
    if to_status not in allowed:
        raise HTTPException(status_code=422, detail=f"Cannot transition from {txn.status} to {to_status}")
    from_status = txn.status
    _add_event(db, txn, from_status, to_status, note, actor_user_id)
    txn.status = to_status
    if to_status == "SETTLED":
        txn.settled_at = utcnow()
        _post_ledger(db, txn)
        _update_obligation(db, txn)
        _issue_receipt(db, txn)
        from app.services.notifications.dispatcher import notify_payment_settled

        notify_payment_settled(db, txn)
        if txn.collection_id:
            col = db.get(Collection, txn.collection_id)
            if col:
                col.status = "COMPLETED"
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


def complete_payment_happy_path(db: Session, transaction_id: str, actor_user_id: Optional[str] = None) -> Transaction:
    txn = db.get(Transaction, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if txn.status == "REJECTED":
        return txn

    # MoMo must settle only after Campay confirms SUCCESSFUL
    if txn.payment_provider == "CAMPAY" and txn.provider_reference:
        from app.services.providers.campay import CampayClient

        client = CampayClient(db)
        status_result = client.get_transaction_status(txn.provider_reference)
        txn.provider_status = status_result.status
        db.flush()
        if status_result.status in ("FAILED", "CANCELED", "CANCELLED"):
            if txn.status != "REJECTED":
                txn = advance_transaction(db, txn, "REJECTED", actor_user_id, f"Campay {status_result.status}")
            return txn
        if status_result.status not in ("SUCCESSFUL", "SUCCESS", "COMPLETED") and not client.mock:
            # Leave in PROCESSING until webhook/poll confirms
            db.commit()
            db.refresh(txn)
            return txn

    for state, note in [
        ("PROCESSING", "Payment processing"),
        ("DEBITED", "Customer account debited via Campay" if txn.payment_provider == "CAMPAY" else "Customer account debited"),
        ("CREDITED", "Council credited"),
        ("SETTLED", "Settlement completed"),
    ]:
        if txn.status == "REJECTED":
            break
        if txn.status != state:
            txn = advance_transaction(db, txn, state, actor_user_id, note)
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
