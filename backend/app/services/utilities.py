"""Utility / bill-pay catalog and payment orchestration."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.base import new_id, utcnow
from app.models.payer import Payer
from app.models.receipt import Receipt
from app.models.transaction import Collection, IdempotencyKey, Transaction
from app.models.utility import UtilityPaymentDetail, UtilityService
from app.services.audit import write_audit
from app.services.payments import (
    _add_event,
    _next_ref,
    advance_transaction,
    mark_payer_debit_failed,
)
from app.services.providers.campay import CampayClient, record_intent


def apply_fee(fee_type: str, fee_value: Decimal, amount: Decimal) -> Decimal:
    if fee_type == "PERCENT":
        return (amount * fee_value / Decimal("100")).quantize(Decimal("0.01"))
    return Decimal(fee_value).quantize(Decimal("0.01"))


def service_to_dict(svc: UtilityService, *, include_admin: bool = False) -> dict:
    data = {
        "utility_service_id": svc.utility_service_id,
        "code": svc.code,
        "name": svc.name,
        "description": svc.description,
        "category": svc.category,
        "icon_key": svc.icon_key,
        "accent_color": svc.accent_color,
        "fee_type": svc.fee_type,
        "fee_value": str(svc.fee_value),
        "currency": svc.currency,
        "accept_meter_number": bool(svc.accept_meter_number),
        "accept_bill_number": bool(svc.accept_bill_number),
        "sort_order": svc.sort_order,
        "status": svc.status,
        "provider_hint": svc.provider_hint,
    }
    if include_admin:
        data["created_at"] = svc.created_at
        data["updated_at"] = svc.updated_at
    return data


def list_store_services(db: Session) -> list[UtilityService]:
    return (
        db.query(UtilityService)
        .filter(UtilityService.status == "ACTIVE")
        .order_by(UtilityService.sort_order.asc(), UtilityService.name.asc())
        .all()
    )


def list_admin_services(db: Session) -> list[UtilityService]:
    return db.query(UtilityService).order_by(UtilityService.sort_order.asc(), UtilityService.name.asc()).all()


def get_service(db: Session, service_id: str) -> UtilityService:
    svc = db.get(UtilityService, service_id)
    if not svc:
        raise HTTPException(status_code=404, detail="Utility service not found")
    return svc


def create_service(db: Session, data: dict, actor_user_id: Optional[str] = None) -> UtilityService:
    code = (data.get("code") or "").strip().upper()
    if not code:
        raise HTTPException(status_code=422, detail="code required")
    if db.query(UtilityService).filter(UtilityService.code == code).first():
        raise HTTPException(status_code=422, detail="code already exists")
    if not data.get("accept_meter_number") and not data.get("accept_bill_number"):
        raise HTTPException(status_code=422, detail="Enable meter number and/or bill number")
    svc = UtilityService(
        code=code,
        name=(data.get("name") or "").strip() or code,
        description=data.get("description"),
        category=(data.get("category") or "UTILITY").strip().upper(),
        icon_key=data.get("icon_key") or "bolt",
        accent_color=data.get("accent_color") or "#1f6b4a",
        fee_type=(data.get("fee_type") or "FLAT").upper(),
        fee_value=Decimal(str(data.get("fee_value") if data.get("fee_value") is not None else "500")),
        currency=data.get("currency") or "XAF",
        accept_meter_number=bool(data.get("accept_meter_number", True)),
        accept_bill_number=bool(data.get("accept_bill_number", True)),
        sort_order=int(data.get("sort_order") or 100),
        provider_hint=data.get("provider_hint"),
        status=(data.get("status") or "ACTIVE").upper(),
    )
    db.add(svc)
    db.flush()
    write_audit(
        db,
        actor_user_id=actor_user_id,
        tenant_id=None,
        entity_type="utility_service",
        entity_id=svc.utility_service_id,
        action="CREATE",
        after=service_to_dict(svc, include_admin=True),
    )
    db.commit()
    db.refresh(svc)
    return svc


def update_service(db: Session, service_id: str, data: dict, actor_user_id: Optional[str] = None) -> UtilityService:
    svc = get_service(db, service_id)
    before = service_to_dict(svc, include_admin=True)
    for key in (
        "name",
        "description",
        "category",
        "icon_key",
        "accent_color",
        "fee_type",
        "currency",
        "provider_hint",
    ):
        if key in data and data[key] is not None:
            setattr(svc, key, data[key] if key != "fee_type" and key != "category" else str(data[key]).upper())
    if "fee_value" in data and data["fee_value"] is not None:
        svc.fee_value = Decimal(str(data["fee_value"]))
    if "accept_meter_number" in data:
        svc.accept_meter_number = bool(data["accept_meter_number"])
    if "accept_bill_number" in data:
        svc.accept_bill_number = bool(data["accept_bill_number"])
    if "sort_order" in data and data["sort_order"] is not None:
        svc.sort_order = int(data["sort_order"])
    if "status" in data and data["status"]:
        status = str(data["status"]).upper()
        if status not in ("ACTIVE", "DISABLED", "INACTIVE"):
            raise HTTPException(status_code=422, detail="Invalid status")
        svc.status = status
    if not svc.accept_meter_number and not svc.accept_bill_number:
        raise HTTPException(status_code=422, detail="Enable meter number and/or bill number")
    write_audit(
        db,
        actor_user_id=actor_user_id,
        tenant_id=None,
        entity_type="utility_service",
        entity_id=svc.utility_service_id,
        action="UPDATE",
        before=before,
        after=service_to_dict(svc, include_admin=True),
    )
    db.commit()
    db.refresh(svc)
    return svc


def quote_utility(db: Session, service_id: str, amount: Decimal) -> dict:
    svc = get_service(db, service_id)
    if svc.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Service is disabled")
    if amount <= 0:
        raise HTTPException(status_code=422, detail="amount must be positive")
    fee = apply_fee(svc.fee_type, svc.fee_value, amount)
    return {
        "utility_service_id": svc.utility_service_id,
        "service_name": svc.name,
        "service_code": svc.code,
        "bill_amount": str(amount.quantize(Decimal("0.01"))),
        "service_fee": str(fee),
        "total_amount": str((amount + fee).quantize(Decimal("0.01"))),
        "currency": svc.currency,
        "fee_type": svc.fee_type,
        "fee_value": str(svc.fee_value),
        "accept_meter_number": bool(svc.accept_meter_number),
        "accept_bill_number": bool(svc.accept_bill_number),
    }


def _parse_amount(raw) -> Decimal:
    try:
        amount = Decimal(str(raw)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError) as exc:
        raise HTTPException(status_code=422, detail="Invalid amount") from exc
    if amount <= 0:
        raise HTTPException(status_code=422, detail="amount must be positive")
    return amount


def _resolve_reference(svc: UtilityService, meter_number: Optional[str], bill_number: Optional[str]) -> tuple[str, Optional[str], Optional[str]]:
    meter = (meter_number or "").strip() or None
    bill = (bill_number or "").strip() or None
    if meter and bill:
        raise HTTPException(status_code=422, detail="Provide meter number or bill number, not both")
    if not meter and not bill:
        raise HTTPException(status_code=422, detail="Provide meter number or bill number")
    if meter:
        if not svc.accept_meter_number:
            raise HTTPException(status_code=422, detail="This service does not accept meter numbers")
        return "METER", meter, None
    if not svc.accept_bill_number:
        raise HTTPException(status_code=422, detail="This service does not accept bill numbers")
    return "BILL", None, bill


def initiate_utility_payment(
    db: Session,
    payer: Payer,
    *,
    utility_service_id: str,
    amount,
    meter_number: Optional[str],
    bill_number: Optional[str],
    phone_number: Optional[str],
    idempotency_key: str,
    actor_user_id: Optional[str] = None,
    force_fail: bool = False,
) -> Transaction:
    if not idempotency_key:
        raise HTTPException(status_code=422, detail="idempotency_key required")
    existing = (
        db.query(IdempotencyKey)
        .filter(IdempotencyKey.key_value == idempotency_key, IdempotencyKey.scope == "utility_payment")
        .first()
    )
    if existing and existing.response_ref:
        txn = db.get(Transaction, existing.response_ref)
        if txn:
            return txn

    svc = get_service(db, utility_service_id)
    if svc.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Service is disabled")
    if not payer.tenant_id or not payer.current_geographic_unit_id:
        raise HTTPException(status_code=422, detail="Payer must have an operating council/zone")

    bill_amount = _parse_amount(amount)
    ref_type, meter, bill = _resolve_reference(svc, meter_number, bill_number)
    fee = apply_fee(svc.fee_type, svc.fee_value, bill_amount)
    total = bill_amount + fee
    phone = (phone_number or payer.phone_number or "").strip()
    if not phone:
        raise HTTPException(status_code=422, detail="phone_number required for Mobile Money debit")

    collection = Collection(
        payer_id=payer.payer_id,
        tenant_id=payer.tenant_id,
        geographic_unit_id=payer.current_geographic_unit_id,
        amount=bill_amount,
        currency=svc.currency,
        status="PENDING",
    )
    db.add(collection)
    db.flush()

    txn = Transaction(
        transaction_reference=_next_ref(db, "UTL"),
        correlation_id=new_id("cor_"),
        idempotency_key=idempotency_key,
        payer_id=payer.payer_id,
        transaction_tenant_id=payer.tenant_id,
        transaction_geographic_unit_id=payer.current_geographic_unit_id,
        collection_id=collection.collection_id,
        amount=bill_amount,
        service_fee=fee,
        commission_amount=Decimal("0"),
        total_amount=total,
        currency=svc.currency,
        payment_channel="MOBILE_MONEY",
        payment_provider="CAMPAY",
        payer_msisdn=phone,
        product_type="UTILITY",
        status="INITIATED",
        initiated_at=utcnow(),
    )
    db.add(txn)
    db.flush()
    _add_event(db, txn, None, "INITIATED", f"Utility payment initiated — {svc.name}", actor_user_id)

    detail = UtilityPaymentDetail(
        transaction_id=txn.transaction_id,
        utility_service_id=svc.utility_service_id,
        reference_type=ref_type,
        meter_number=meter,
        bill_number=bill,
        account_label=meter or bill,
        service_name_snapshot=svc.name,
        service_code_snapshot=svc.code,
        bill_amount=bill_amount,
    )
    db.add(detail)
    db.flush()

    client = CampayClient(db)
    if force_fail:
        from app.services.providers.campay import CampayResult

        result = CampayResult(
            ok=False,
            reference=None,
            status="FAILED",
            raw={},
            error="Utility payment failed: MoMo collection declined (simulated)",
        )
    else:
        result = client.collect(
            amount=total,
            phone=phone,
            description=f"EasyPay {svc.code} bill {meter or bill}",
            external_reference=txn.transaction_reference,
            currency=svc.currency,
        )
    record_intent(
        db,
        operation="COLLECT",
        entity_type="transaction",
        entity_id=txn.transaction_id,
        tenant_id=txn.transaction_tenant_id,
        amount=str(total),
        currency=svc.currency,
        destination=phone,
        result=result,
        external_reference=txn.transaction_reference,
        payout_method="MOMO",
    )
    txn.provider_reference = result.reference
    txn.provider_status = result.status

    if not result.ok:
        mark_payer_debit_failed(
            db,
            txn,
            result.error or "Utility payment failed: MoMo collection was declined",
            actor_user_id,
        )
        collection.status = "FAILED"
    else:
        # Utility path: debit payer → credit utility provider → settle (receipt + email on SETTLED)
        advance_transaction(db, txn, "PROCESSING", actor_user_id, "Payment processing")
        advance_transaction(db, txn, "DEBITED", actor_user_id, "Customer account debited via Campay")
        advance_transaction(
            db,
            txn,
            "CREDITED",
            actor_user_id,
            f"{svc.name} credited ({ref_type}: {meter or bill})",
        )
        advance_transaction(db, txn, "SETTLED", actor_user_id, f"{svc.name} bill payment settled")
        collection.status = "COMPLETED"
        receipt = db.query(Receipt).filter(Receipt.transaction_id == txn.transaction_id).first()
        if receipt:
            receipt.revenue_name = f"{svc.name} ({ref_type}: {meter or bill})"
            receipt.council_name = "EasyPay Utilities"
            detail.receipt_emailed_at = utcnow()
        # notify_payment_settled already invoked inside advance_transaction(SETTLED)

    db.add(IdempotencyKey(key_value=idempotency_key, scope="utility_payment", response_ref=txn.transaction_id))
    write_audit(
        db,
        actor_user_id=actor_user_id,
        tenant_id=payer.tenant_id,
        entity_type="transaction",
        entity_id=txn.transaction_id,
        action="UTILITY_INITIATE",
        after={
            "product_type": "UTILITY",
            "service": svc.code,
            "amount": str(bill_amount),
            "total": str(total),
            "status": txn.status,
        },
    )
    db.commit()
    db.refresh(txn)
    return txn


def utility_detail_for_txn(db: Session, transaction_id: str) -> Optional[UtilityPaymentDetail]:
    return (
        db.query(UtilityPaymentDetail)
        .filter(UtilityPaymentDetail.transaction_id == transaction_id)
        .first()
    )


def ensure_sample_utility_services(db: Session) -> dict:
    """Seed ENEO (light) + CAMWATER (water) demo services."""
    specs = [
        {
            "code": "ENEO",
            "name": "ENEO Electricity",
            "description": "Pay your electricity bill with meter number or bill number.",
            "category": "ELECTRICITY",
            "icon_key": "bolt",
            "accent_color": "#e8b84a",
            "fee_type": "FLAT",
            "fee_value": "500",
            "accept_meter_number": True,
            "accept_bill_number": True,
            "sort_order": 10,
            "provider_hint": "ENEO",
            "status": "ACTIVE",
        },
        {
            "code": "CAMWATER",
            "name": "CAMWATER Water",
            "description": "Pay your water bill with meter number or bill number.",
            "category": "WATER",
            "icon_key": "droplet",
            "accent_color": "#2b6cb0",
            "fee_type": "FLAT",
            "fee_value": "300",
            "accept_meter_number": True,
            "accept_bill_number": True,
            "sort_order": 20,
            "provider_hint": "CAMWATER",
            "status": "ACTIVE",
        },
        {
            "code": "DEMO-DISABLED",
            "name": "Demo Disabled Service",
            "description": "Hidden from store while DISABLED — used for admin demos.",
            "category": "OTHER",
            "icon_key": "grid",
            "accent_color": "#718096",
            "fee_type": "PERCENT",
            "fee_value": "1.5",
            "accept_meter_number": True,
            "accept_bill_number": False,
            "sort_order": 90,
            "status": "DISABLED",
        },
    ]
    out = {}
    for spec in specs:
        row = db.query(UtilityService).filter(UtilityService.code == spec["code"]).first()
        if not row:
            row = UtilityService(
                code=spec["code"],
                name=spec["name"],
                description=spec["description"],
                category=spec["category"],
                icon_key=spec["icon_key"],
                accent_color=spec["accent_color"],
                fee_type=spec["fee_type"],
                fee_value=Decimal(spec["fee_value"]),
                accept_meter_number=spec["accept_meter_number"],
                accept_bill_number=spec["accept_bill_number"],
                sort_order=spec["sort_order"],
                provider_hint=spec.get("provider_hint"),
                status=spec["status"],
            )
            db.add(row)
        else:
            for k, v in spec.items():
                if k == "fee_value":
                    setattr(row, k, Decimal(v))
                else:
                    setattr(row, k, v)
        db.flush()
        out[spec["code"]] = row.utility_service_id
    db.commit()
    return out
