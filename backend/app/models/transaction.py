from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, StatusMixin, new_id, utcnow


class Collection(Base, TimestampMixin, StatusMixin):
    __tablename__ = "collections"

    collection_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("col_"))
    payer_id: Mapped[str] = mapped_column(String(36), ForeignKey("payers.payer_id"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    geographic_unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("geographic_units.geographic_unit_id"), nullable=False, index=True
    )
    obligation_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("obligations.obligation_id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="XAF")


class Transaction(Base, TimestampMixin, StatusMixin):
    __tablename__ = "transactions"

    transaction_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("txn_"))
    transaction_reference: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), unique=True, index=True)
    payer_id: Mapped[str] = mapped_column(String(36), ForeignKey("payers.payer_id"), nullable=False, index=True)
    # Immutable snapshot fields — never rewrite after posting
    transaction_tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    transaction_geographic_unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("geographic_units.geographic_unit_id"), nullable=False, index=True
    )
    obligation_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("obligations.obligation_id"))
    revenue_type_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("revenue_types.revenue_type_id"))
    collection_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("collections.collection_id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    service_fee: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="XAF")
    payment_channel: Mapped[str] = mapped_column(String(64), default="MOBILE_MONEY")
    payment_provider: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    provider_reference: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    provider_status: Mapped[Optional[str]] = mapped_column(String(32))
    payer_msisdn: Mapped[Optional[str]] = mapped_column(String(32))
    initiated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # status: INITIATED | PROCESSING | DEBITED | CREDITED | SETTLED | FAILED
    # SETTLED and FAILED are peer terminal outcomes; REJECTED is a legacy alias of FAILED


class TransactionEvent(Base, TimestampMixin):
    __tablename__ = "transaction_events"

    transaction_event_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("tev_"))
    transaction_id: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.transaction_id"), nullable=False, index=True)
    from_status: Mapped[Optional[str]] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text)
    actor_user_id: Mapped[Optional[str]] = mapped_column(String(36))


class IdempotencyKey(Base, TimestampMixin):
    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("key_value", "scope", name="uq_idem_key_scope"),)

    idempotency_key_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("idk_"))
    key_value: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(64), default="payment")
    response_ref: Mapped[Optional[str]] = mapped_column(String(64))
    request_hash: Mapped[Optional[str]] = mapped_column(String(128))
