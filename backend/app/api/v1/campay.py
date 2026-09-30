"""Campay collection, withdrawal, disbursement, bank transfer, and status APIs."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.deps import DbDep, SystemAdminDep, UserDep, require_permissions
from app.models.provider import ProviderPaymentIntent
from app.services.providers.campay import CampayClient, record_intent, sync_intent_status

router = APIRouter(prefix="/campay", tags=["campay"])


class CollectIn(BaseModel):
    amount: float = Field(gt=0)
    phone_number: str
    description: str = "EasyPay collection"
    external_reference: str
    currency: str = "XAF"
    entity_type: str = "manual"
    entity_id: Optional[str] = None


class WithdrawIn(BaseModel):
    amount: float = Field(gt=0)
    phone_number: str
    description: str = "EasyPay withdrawal"
    external_reference: str
    currency: str = "XAF"
    entity_type: str = "manual"
    entity_id: Optional[str] = None


class DisburseIn(BaseModel):
    amount: float = Field(gt=0)
    phone_number: str
    description: str = "EasyPay disbursement"
    external_reference: str
    currency: str = "XAF"
    entity_type: str = "manual"
    entity_id: Optional[str] = None


class BankTransferIn(BaseModel):
    amount: float = Field(gt=0)
    account_number: str
    account_name: str
    bank_code: str
    description: str = "EasyPay bank payout"
    external_reference: str
    currency: str = "XAF"
    entity_type: str = "manual"
    entity_id: Optional[str] = None


def _intent_out(intent: ProviderPaymentIntent) -> dict:
    return {
        "intent_id": intent.intent_id,
        "operation": intent.operation,
        "provider_reference": intent.provider_reference,
        "external_reference": intent.external_reference,
        "status": intent.status,
        "amount": intent.amount,
        "currency": intent.currency,
        "destination": intent.destination,
        "payout_method": intent.payout_method,
        "error_message": intent.error_message,
        "entity_type": intent.entity_type,
        "entity_id": intent.entity_id,
    }


@router.post("/collect")
def campay_collect(body: CollectIn, db: DbDep, current=Depends(require_permissions("settlements:write", "platforms:write"))):
    client = CampayClient(db)
    result = client.collect(
        amount=body.amount,
        phone=body.phone_number,
        description=body.description,
        external_reference=body.external_reference,
        currency=body.currency,
    )
    intent = record_intent(
        db,
        operation="COLLECT",
        entity_type=body.entity_type,
        entity_id=body.entity_id or body.external_reference,
        tenant_id=current.tenant_id,
        amount=str(body.amount),
        currency=body.currency,
        destination=body.phone_number,
        result=result,
        external_reference=body.external_reference,
        payout_method="MOMO",
    )
    db.commit()
    if not result.ok:
        raise HTTPException(status_code=502, detail=result.error or "Campay collect failed")
    return _intent_out(intent)


@router.post("/withdraw")
def campay_withdraw(body: WithdrawIn, db: DbDep, current=Depends(require_permissions("settlements:write", "platforms:write"))):
    client = CampayClient(db)
    result = client.withdraw(
        amount=body.amount,
        phone=body.phone_number,
        description=body.description,
        external_reference=body.external_reference,
        currency=body.currency,
    )
    intent = record_intent(
        db,
        operation="WITHDRAW",
        entity_type=body.entity_type,
        entity_id=body.entity_id or body.external_reference,
        tenant_id=current.tenant_id,
        amount=str(body.amount),
        currency=body.currency,
        destination=body.phone_number,
        result=result,
        external_reference=body.external_reference,
        payout_method="MOMO",
    )
    db.commit()
    if not result.ok:
        raise HTTPException(status_code=502, detail=result.error or "Campay withdraw failed")
    return _intent_out(intent)


@router.post("/disburse")
def campay_disburse(body: DisburseIn, db: DbDep, current=Depends(require_permissions("settlements:write", "platforms:write"))):
    client = CampayClient(db)
    result = client.disburse(
        amount=body.amount,
        phone=body.phone_number,
        description=body.description,
        external_reference=body.external_reference,
        currency=body.currency,
    )
    intent = record_intent(
        db,
        operation="DISBURSE",
        entity_type=body.entity_type,
        entity_id=body.entity_id or body.external_reference,
        tenant_id=current.tenant_id,
        amount=str(body.amount),
        currency=body.currency,
        destination=body.phone_number,
        result=result,
        external_reference=body.external_reference,
        payout_method="MOMO",
    )
    db.commit()
    if not result.ok:
        raise HTTPException(status_code=502, detail=result.error or "Campay disburse failed")
    return _intent_out(intent)


@router.post("/bank-transfer")
def campay_bank_transfer(body: BankTransferIn, db: DbDep, current=Depends(require_permissions("settlements:write", "platforms:write"))):
    client = CampayClient(db)
    result = client.bank_transfer(
        amount=body.amount,
        account_number=body.account_number,
        account_name=body.account_name,
        bank_code=body.bank_code,
        description=body.description,
        external_reference=body.external_reference,
        currency=body.currency,
    )
    intent = record_intent(
        db,
        operation="BANK_TRANSFER",
        entity_type=body.entity_type,
        entity_id=body.entity_id or body.external_reference,
        tenant_id=current.tenant_id,
        amount=str(body.amount),
        currency=body.currency,
        destination=body.account_number,
        result=result,
        external_reference=body.external_reference,
        payout_method="BANK",
    )
    db.commit()
    if not result.ok:
        raise HTTPException(status_code=502, detail=result.error or "Campay bank transfer failed")
    return _intent_out(intent)


@router.get("/transactions/{reference}")
def campay_status(reference: str, db: DbDep, current=Depends(require_permissions("settlements:read", "reports:read", "platforms:write"))):
    client = CampayClient(db)
    result = client.get_transaction_status(reference)
    intent = (
        db.query(ProviderPaymentIntent)
        .filter(ProviderPaymentIntent.provider_reference == reference)
        .order_by(ProviderPaymentIntent.created_at.desc())
        .first()
    )
    if intent:
        sync_intent_status(db, intent)
        db.commit()
    return {
        "reference": result.reference or reference,
        "status": result.status,
        "ok": result.ok,
        "error": result.error,
        "raw": result.raw,
        "intent": _intent_out(intent) if intent else None,
    }


@router.post("/webhook")
def campay_webhook(payload: dict, db: DbDep):
    """Public webhook for Campay status callbacks — advances linked MoMo payments."""
    reference = payload.get("reference") or payload.get("transaction_reference")
    status = str(payload.get("status") or "").upper()
    if not reference:
        raise HTTPException(status_code=422, detail="reference required")
    intent = (
        db.query(ProviderPaymentIntent)
        .filter(ProviderPaymentIntent.provider_reference == reference)
        .order_by(ProviderPaymentIntent.created_at.desc())
        .first()
    )
    if intent:
        intent.status = status or intent.status
        intent.raw_response = str(payload)[:8000]
    if intent and intent.entity_type == "transaction" and status in ("SUCCESSFUL", "SUCCESS", "COMPLETED"):
        from app.services.payments import complete_payment_happy_path

        complete_payment_happy_path(db, intent.entity_id, actor_user_id=None)
    elif intent and intent.entity_type == "transaction" and status in ("FAILED", "CANCELED", "CANCELLED"):
        from app.models.transaction import Transaction
        from app.services.payments import mark_payer_debit_failed

        txn = db.get(Transaction, intent.entity_id)
        if txn and txn.status not in ("SETTLED", "FAILED", "REJECTED", "MANUAL_INTERVENTION", "CREDITED"):
            try:
                mark_payer_debit_failed(
                    db,
                    txn,
                    f"Payer debit failed: provider status {status}",
                    actor_user_id=None,
                )
            except Exception:
                txn.status = "FAILED"
                txn.failure_stage = "DEBIT"
                txn.failure_reason = f"Payer debit failed: provider status {status}"
                db.commit()
    else:
        db.commit()
    return {"ok": True, "reference": reference, "status": status}
