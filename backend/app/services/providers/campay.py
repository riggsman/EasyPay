"""Campay API client — collection, withdrawal, disbursement, and bank transfer.

All Mobile Money collections/withdrawals for EasyPay go through this adapter.
Bank reconciliation payouts use Campay's bank transfer service.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Optional
from urllib import error, parse, request

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import utcnow
from app.models.provider import ProviderPaymentIntent
from app.services.providers import store as provider_store

logger = logging.getLogger(__name__)


@dataclass
class CampayResult:
    ok: bool
    reference: Optional[str]
    status: str
    raw: dict[str, Any]
    error: Optional[str] = None


class CampayClient:
    def __init__(self, db: Session):
        self.db = db
        settings = get_settings()
        secrets = provider_store.get_provider_secrets(db, provider_store.PROVIDER_CAMPAY)
        row = provider_store.get_provider_row(db, provider_store.PROVIDER_CAMPAY)
        self.enabled = bool(row and row.enabled)
        self.username = secrets.get("username") or secrets.get("app_username") or ""
        self.password = secrets.get("password") or secrets.get("app_password") or ""
        self.base_url = (secrets.get("base_url") or settings.CAMPAY_BASE_URL).rstrip("/")
        self.mock = bool(secrets.get("mock", settings.CAMPAY_MOCK))
        self._token: Optional[str] = None

    def ensure_ready(self) -> None:
        if not self.enabled and not self.mock:
            raise RuntimeError("Campay provider is disabled")
        if not self.mock and (not self.username or not self.password):
            raise RuntimeError("Campay credentials are not configured")

    def _http(self, method: str, path: str, body: Optional[dict] = None, auth: bool = True) -> dict[str, Any]:
        if self.mock:
            return self._mock_response(method, path, body or {})
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if auth:
            headers["Authorization"] = f"Token {self.get_token()}"
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        req = request.Request(url, data=data, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=45) as resp:
                payload = resp.read().decode("utf-8")
                return json.loads(payload) if payload else {}
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Campay HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Campay network error: {exc.reason}") from exc

    def _mock_response(self, method: str, path: str, body: dict) -> dict[str, Any]:
        ref = str(uuid.uuid4())
        if path.endswith("/token/"):
            return {"token": f"mock-token-{ref[:8]}", "expires_in": 3600}
        if "/transaction/" in path:
            return {
                "reference": path.strip("/").split("/")[-1],
                "status": "SUCCESSFUL",
                "amount": body.get("amount") or "0",
                "currency": "XAF",
                "operator": "MTN",
            }
        return {
            "reference": ref,
            "status": "PENDING",
            "amount": str(body.get("amount", "")),
            "currency": body.get("currency", "XAF"),
            "external_reference": body.get("external_reference"),
            "ussd_code": "*126#" if "collect" in path else None,
            "operator": body.get("operator") or "MTN",
            "mock": True,
        }

    def get_token(self) -> str:
        if self._token:
            return self._token
        data = self._http(
            "POST",
            "/token/",
            {"username": self.username, "password": self.password},
            auth=False,
        )
        token = data.get("token") or data.get("access")
        if not token:
            raise RuntimeError("Campay token response missing token")
        self._token = token
        return token

    def collect(
        self,
        *,
        amount: str | int | float,
        phone: str,
        description: str,
        external_reference: str,
        currency: str = "XAF",
    ) -> CampayResult:
        self.ensure_ready()
        phone = _normalize_cm_phone(phone)
        try:
            raw = self._http(
                "POST",
                "/collect/",
                {
                    "amount": str(int(float(amount))),
                    "currency": currency,
                    "from": phone,
                    "description": description[:200],
                    "external_reference": external_reference,
                },
            )
            return CampayResult(
                ok=True,
                reference=raw.get("reference"),
                status=str(raw.get("status") or "PENDING").upper(),
                raw=raw,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Campay collect failed")
            return CampayResult(ok=False, reference=None, status="FAILED", raw={}, error=str(exc))

    def withdraw(
        self,
        *,
        amount: str | int | float,
        phone: str,
        description: str,
        external_reference: str,
        currency: str = "XAF",
    ) -> CampayResult:
        self.ensure_ready()
        phone = _normalize_cm_phone(phone)
        try:
            raw = self._http(
                "POST",
                "/withdraw/",
                {
                    "amount": str(int(float(amount))),
                    "currency": currency,
                    "to": phone,
                    "description": description[:200],
                    "external_reference": external_reference,
                },
            )
            return CampayResult(
                ok=True,
                reference=raw.get("reference"),
                status=str(raw.get("status") or "PENDING").upper(),
                raw=raw,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Campay withdraw failed")
            return CampayResult(ok=False, reference=None, status="FAILED", raw={}, error=str(exc))

    def disburse(
        self,
        *,
        amount: str | int | float,
        phone: str,
        description: str,
        external_reference: str,
        currency: str = "XAF",
    ) -> CampayResult:
        """Disbursement to MoMo — uses Campay withdraw under the hood."""
        return self.withdraw(
            amount=amount,
            phone=phone,
            description=description,
            external_reference=external_reference,
            currency=currency,
        )

    def bank_transfer(
        self,
        *,
        amount: str | int | float,
        account_number: str,
        account_name: str,
        bank_code: str,
        description: str,
        external_reference: str,
        currency: str = "XAF",
    ) -> CampayResult:
        """Bank payout via Campay bank service (reconciliation / settlement)."""
        self.ensure_ready()
        try:
            # Campay bank transfer surface — path configurable via secrets
            secrets = provider_store.get_provider_secrets(self.db, provider_store.PROVIDER_CAMPAY)
            path = secrets.get("bank_transfer_path") or "/withdraw/"
            payload = {
                "amount": str(int(float(amount))),
                "currency": currency,
                "to": account_number,
                "description": description[:200],
                "external_reference": external_reference,
                "payment_method": "BANK",
                "bank_code": bank_code,
                "account_name": account_name,
            }
            raw = self._http("POST", path if path.startswith("/") else f"/{path}", payload)
            return CampayResult(
                ok=True,
                reference=raw.get("reference"),
                status=str(raw.get("status") or "PENDING").upper(),
                raw=raw,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Campay bank transfer failed")
            return CampayResult(ok=False, reference=None, status="FAILED", raw={}, error=str(exc))

    def get_transaction_status(self, reference: str) -> CampayResult:
        self.ensure_ready()
        try:
            raw = self._http("GET", f"/transaction/{parse.quote(reference)}/")
            return CampayResult(
                ok=True,
                reference=raw.get("reference") or reference,
                status=str(raw.get("status") or "PENDING").upper(),
                raw=raw,
            )
        except Exception as exc:  # noqa: BLE001
            return CampayResult(ok=False, reference=reference, status="UNKNOWN", raw={}, error=str(exc))


def _normalize_cm_phone(phone: str) -> str:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if digits.startswith("237"):
        return digits
    if len(digits) == 9:
        return f"237{digits}"
    return digits


def record_intent(
    db: Session,
    *,
    operation: str,
    entity_type: str,
    entity_id: str,
    tenant_id: Optional[str],
    amount: str,
    currency: str,
    destination: Optional[str],
    result: CampayResult,
    external_reference: str,
    payout_method: Optional[str] = None,
) -> ProviderPaymentIntent:
    intent = ProviderPaymentIntent(
        provider_code=provider_store.PROVIDER_CAMPAY,
        operation=operation,
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=tenant_id,
        amount=str(amount),
        currency=currency,
        destination=destination,
        provider_reference=result.reference,
        external_reference=external_reference,
        status=result.status if result.ok else "FAILED",
        payout_method=payout_method,
        raw_response=json.dumps(result.raw)[:8000] if result.raw else None,
        error_message=result.error,
    )
    db.add(intent)
    db.flush()
    return intent


def sync_intent_status(db: Session, intent: ProviderPaymentIntent) -> ProviderPaymentIntent:
    if not intent.provider_reference:
        return intent
    client = CampayClient(db)
    result = client.get_transaction_status(intent.provider_reference)
    intent.status = result.status
    intent.raw_response = json.dumps(result.raw)[:8000] if result.raw else intent.raw_response
    intent.error_message = result.error
    intent.updated_at = utcnow()
    db.flush()
    return intent
