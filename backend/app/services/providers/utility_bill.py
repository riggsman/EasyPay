"""Utility bill provider adapter (ENEO, CAMWATER, …).

Part-2 of a utility payment: called only after the payer MoMo debit is confirmed.
In development/mock mode this records a successful provider acknowledgment without
an external HTTP call; live credentials can be wired later via provider_store.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.provider import ProviderPaymentIntent
from app.services.providers import store as provider_store

logger = logging.getLogger(__name__)

PROVIDER_UTILITY_BILL = "UTILITY_BILL"


@dataclass
class UtilityProviderResult:
    ok: bool
    reference: Optional[str]
    status: str
    raw: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class UtilityBillClient:
    """Sends bill-payment requests to the utility operator after debit success."""

    def __init__(self, db: Session):
        self.db = db
        settings = get_settings()
        # Optional future: dedicated utility provider secrets. Default = mock.
        secrets = {}
        try:
            secrets = provider_store.get_provider_secrets(db, PROVIDER_UTILITY_BILL) or {}
        except Exception:  # noqa: BLE001
            secrets = {}
        self.mock = bool(secrets.get("mock", True if settings.APP_ENV != "production" else settings.CAMPAY_MOCK))
        self.base_url = (secrets.get("base_url") or "").rstrip("/")
        self.api_key = secrets.get("api_key") or ""

    def pay_bill(
        self,
        *,
        provider_hint: str,
        service_code: str,
        service_name: str,
        amount,
        currency: str,
        reference_type: str,
        meter_number: Optional[str],
        bill_number: Optional[str],
        external_reference: str,
    ) -> UtilityProviderResult:
        account = meter_number or bill_number or ""
        if not account:
            return UtilityProviderResult(
                ok=False,
                reference=None,
                status="FAILED",
                error="Utility provider request blocked: meter/bill reference missing",
            )
        # Simulation hook
        if "FAIL" in account.upper():
            return UtilityProviderResult(
                ok=False,
                reference=None,
                status="FAILED",
                error=f"Utility provider rejected account {account} (simulated)",
            )

        if self.mock or not self.base_url:
            ref = f"UTL-{provider_hint or service_code}-{uuid.uuid4().hex[:10]}"
            return UtilityProviderResult(
                ok=True,
                reference=ref,
                status="SUCCESSFUL",
                raw={
                    "mock": True,
                    "provider": provider_hint or service_code,
                    "service_name": service_name,
                    "reference_type": reference_type,
                    "account": account,
                    "amount": str(amount),
                    "currency": currency,
                    "external_reference": external_reference,
                },
            )

        # Live hook placeholder — not used until credentials/base_url are configured
        try:
            from urllib import request as urlrequest

            payload = json.dumps(
                {
                    "provider": provider_hint or service_code,
                    "service_code": service_code,
                    "amount": str(amount),
                    "currency": currency,
                    "reference_type": reference_type,
                    "meter_number": meter_number,
                    "bill_number": bill_number,
                    "external_reference": external_reference,
                }
            ).encode("utf-8")
            req = urlrequest.Request(
                f"{self.base_url}/pay",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                method="POST",
            )
            with urlrequest.urlopen(req, timeout=45) as resp:
                body = resp.read().decode("utf-8")
                raw = json.loads(body) if body else {}
            return UtilityProviderResult(
                ok=True,
                reference=raw.get("reference") or external_reference,
                status=str(raw.get("status") or "SUCCESSFUL").upper(),
                raw=raw,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Utility provider pay_bill failed")
            return UtilityProviderResult(
                ok=False,
                reference=None,
                status="FAILED",
                raw={},
                error=str(exc),
            )


def record_utility_intent(
    db: Session,
    *,
    provider_hint: str,
    entity_id: str,
    tenant_id: Optional[str],
    amount: str,
    currency: str,
    destination: Optional[str],
    result: UtilityProviderResult,
    external_reference: str,
) -> ProviderPaymentIntent:
    intent = ProviderPaymentIntent(
        provider_code=(provider_hint or PROVIDER_UTILITY_BILL).upper(),
        operation="UTILITY_PAY",
        entity_type="transaction",
        entity_id=entity_id,
        tenant_id=tenant_id,
        amount=str(amount),
        currency=currency,
        destination=destination,
        provider_reference=result.reference,
        external_reference=external_reference,
        status=result.status if result.ok else "FAILED",
        payout_method="UTILITY",
        raw_response=json.dumps(result.raw)[:8000] if result.raw else None,
        error_message=result.error,
    )
    db.add(intent)
    db.flush()
    return intent
