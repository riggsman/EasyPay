from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- Auth ----
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_type: str
    full_name: Optional[str] = None
    tenant_id: Optional[str] = None
    permissions: List[str] = []


class RefreshRequest(BaseModel):
    refresh_token: str


# ---- Platform / Tenant / Geography ----
class PlatformCreate(BaseModel):
    platform_code: str
    platform_name: str
    legal_name: Optional[str] = None
    registration_number: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    default_currency: str = "XAF"


class PlatformOut(ORMModel):
    platform_id: str
    platform_code: str
    platform_name: str
    legal_name: Optional[str] = None
    default_currency: str
    status: str


class GeographicUnitCreate(BaseModel):
    parent_id: Optional[str] = None
    unit_code: str
    unit_name: str
    unit_type: str
    country_code: Optional[str] = None


class GeographicUnitOut(ORMModel):
    geographic_unit_id: str
    parent_id: Optional[str] = None
    unit_code: str
    unit_name: str
    unit_type: str
    country_code: Optional[str] = None
    status: str


class TenantCreate(BaseModel):
    tenant_code: str
    organization_name: str
    organization_type: str = "COUNCIL"
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    currency: str = "XAF"
    zone_change_mode: str = "IMMEDIATE"
    geographic_unit_id: Optional[str] = None


class TenantOut(ORMModel):
    tenant_id: str
    tenant_code: str
    organization_name: str
    organization_type: str
    currency: str
    status: str
    zone_change_mode: str
    verification: str


class TenantGeoMapCreate(BaseModel):
    tenant_id: str
    geographic_unit_id: str
    relationship_type: str = "PRIMARY_COUNCIL"
    is_primary: bool = True


# ---- Payer ----
class PayerRegisterRequest(BaseModel):
    full_name: str
    business_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    username: str
    password: str
    password_confirm: str
    payer_type: str = "INDIVIDUAL"
    identification_type: Optional[str] = None
    identification_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    geographic_unit_id: str  # council/zone


class PayerOut(ORMModel):
    payer_id: str
    payer_reference: str
    full_name: str
    business_name: Optional[str] = None
    payer_type: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    tenant_id: Optional[str] = None
    current_geographic_unit_id: Optional[str] = None
    status: str


class ZoneChangeRequestIn(BaseModel):
    geographic_unit_id: str
    reason: Optional[str] = None


class ZoneHistoryOut(ORMModel):
    payer_geographic_history_id: str
    geographic_unit_id: str
    tenant_id: Optional[str] = None
    effective_from: datetime
    effective_to: Optional[datetime] = None
    change_reason: Optional[str] = None
    status: str


# ---- Revenue / Obligations ----
class RevenueTypeCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    default_amount: Optional[Decimal] = None
    geographic_unit_id: Optional[str] = None
    currency: str = "XAF"


class RevenueTypeOut(ORMModel):
    revenue_type_id: str
    tenant_id: str
    code: str
    name: str
    default_amount: Optional[Decimal] = None
    currency: str
    status: str
    geographic_unit_id: Optional[str] = None


class FeeConfigCreate(BaseModel):
    fee_type: str = "FLAT"
    fee_value: Decimal
    revenue_type_id: Optional[str] = None
    payment_channel_id: Optional[str] = None
    geographic_unit_id: Optional[str] = None
    currency: str = "XAF"


class ObligationCreate(BaseModel):
    payer_id: str
    revenue_type_id: str
    amount: Decimal
    description: Optional[str] = None
    financial_period_id: Optional[str] = None
    due_date: Optional[datetime] = None


class ObligationOut(ORMModel):
    obligation_id: str
    payer_id: str
    tenant_id: str
    geographic_unit_id: str
    revenue_type_id: str
    description: Optional[str] = None
    amount: Decimal
    balance: Decimal
    currency: str
    status: str
    due_date: Optional[datetime] = None


# ---- Payments ----
class PaymentResolveRequest(BaseModel):
    obligation_id: str
    payment_channel: str = "MOBILE_MONEY"


class PaymentResolveResponse(BaseModel):
    payer_id: str
    obligation_id: str
    tenant_id: str
    geographic_unit_id: str
    council_name: str
    operating_area: str
    revenue_type_id: str
    revenue_name: str
    amount: Decimal
    service_fee: Decimal
    # Hidden from payers — only staff/platform see platform commission
    commission_amount: Optional[Decimal] = None
    total_amount: Decimal
    currency: str
    payment_channel: str


class PaymentInitiateRequest(BaseModel):
    obligation_id: str
    payment_channel: str = "MOBILE_MONEY"
    idempotency_key: str
    phone_number: Optional[str] = None
    # Required for MOBILE_MONEY — charged via Campay collect


class TransactionOut(ORMModel):
    transaction_id: str
    transaction_reference: str
    payer_id: str
    transaction_tenant_id: str
    transaction_geographic_unit_id: str
    obligation_id: Optional[str] = None
    amount: Decimal
    service_fee: Decimal
    # Omitted/null for PAYER responses — council/platform only
    commission_amount: Optional[Decimal] = None
    total_amount: Decimal
    currency: str
    payment_channel: str
    payment_provider: Optional[str] = None
    provider_reference: Optional[str] = None
    provider_status: Optional[str] = None
    payer_msisdn: Optional[str] = None
    status: str
    initiated_at: datetime
    settled_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    failure_stage: Optional[str] = None
    credit_retry_count: int = 0
    credit_destination: Optional[str] = None
    credit_payout_method: Optional[str] = None


class TransactionEventOut(ORMModel):
    from_status: Optional[str] = None
    to_status: str
    label: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime


class TransactionDetailOut(TransactionOut):
    events: List[TransactionEventOut] = []
    receipt_number: Optional[str] = None
    receipt_id: Optional[str] = None
    receipt_pdf_url: Optional[str] = None
    credit_recovery: Optional[dict] = None


class ManualCreditRequest(BaseModel):
    confirm: bool = False
    payout_method: str = "MOMO"
    momo_number: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_account_name: Optional[str] = None
    bank_code: Optional[str] = None
    amount: Optional[Decimal] = None


# ---- Receipts ----
class ReceiptOut(ORMModel):
    receipt_id: str
    receipt_number: str
    verification_token: str
    transaction_id: str
    payer_display_name: str
    council_name: str
    revenue_name: Optional[str] = None
    amount: Decimal
    service_fee: Decimal
    total_amount: Decimal
    currency: str
    payment_date: datetime
    payment_channel: Optional[str] = None
    status: str
    tenant_id: str
    geographic_unit_id: str
    pdf_download_url: Optional[str] = None


class PublicVerifyOut(BaseModel):
    verified: bool
    message: str
    receipt_number: Optional[str] = None
    council_name: Optional[str] = None
    revenue_name: Optional[str] = None
    amount: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    currency: Optional[str] = None
    payment_date: Optional[datetime] = None
    status: Optional[str] = None
    payer_display: Optional[str] = None
    pdf_download_url: Optional[str] = None


# ---- Settlements / Dashboards ----
class SettlementCreateRequest(BaseModel):
    period_start: datetime
    period_end: datetime


class SettlementProcessRequest(BaseModel):
    payout_method: str = "MOMO"
    # MOMO | BANK
    momo_number: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_account_name: Optional[str] = None
    bank_code: Optional[str] = None


class SettlementOut(ORMModel):
    settlement_id: str
    settlement_reference: str
    tenant_id: str
    period_start: datetime
    period_end: datetime
    gross_amount: Decimal
    service_fees: Decimal
    commission_amount: Decimal
    net_amount: Decimal
    payout_method: Optional[str] = None
    payout_destination: Optional[str] = None
    payout_provider_reference: Optional[str] = None
    payout_status: Optional[str] = None
    currency: str
    status: str


class DashboardStats(BaseModel):
    collections_today: Decimal = Decimal("0")
    transactions_today: int = 0
    successful_today: int = 0
    pending_today: int = 0
    rejected_today: int = 0
    outstanding_settlement: Decimal = Decimal("0")
    outstanding_obligations: Decimal = Decimal("0")
    paid_total: Decimal = Decimal("0")
    extras: dict[str, Any] = Field(default_factory=dict)


class MessageOut(BaseModel):
    message: str
    detail: Optional[Any] = None
