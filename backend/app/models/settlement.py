from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, StatusMixin, new_id


class Settlement(Base, TimestampMixin, StatusMixin):
    __tablename__ = "settlements"

    settlement_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("stl_"))
    settlement_reference: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    service_fees: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(8), default="XAF")
    approved_by: Mapped[Optional[str]] = mapped_column(String(36))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    payout_method: Mapped[Optional[str]] = mapped_column(String(32))
    # MOMO | BANK
    payout_destination: Mapped[Optional[str]] = mapped_column(String(128))
    payout_provider_reference: Mapped[Optional[str]] = mapped_column(String(128))
    payout_status: Mapped[Optional[str]] = mapped_column(String(32))
    # status: CALCULATED | PENDING_APPROVAL | APPROVED | PROCESSING | COMPLETED | REJECTED


class SettlementLine(Base, TimestampMixin):
    __tablename__ = "settlement_lines"

    settlement_line_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("sll_"))
    settlement_id: Mapped[str] = mapped_column(String(36), ForeignKey("settlements.settlement_id"), nullable=False, index=True)
    geographic_unit_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    revenue_type_id: Mapped[Optional[str]] = mapped_column(String(36))
    transaction_count: Mapped[int] = mapped_column(default=0)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    service_fees: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))


class ReconciliationRecord(Base, TimestampMixin, StatusMixin):
    __tablename__ = "reconciliation_records"

    reconciliation_record_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("rec_"))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    settlement_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("settlements.settlement_id"))
    transaction_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("transactions.transaction_id"))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    # status: MATCHED | UNMATCHED | EXCEPTION
