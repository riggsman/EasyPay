from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, StatusMixin, new_id


class RevenueType(Base, TimestampMixin, StatusMixin):
    __tablename__ = "revenue_types"

    revenue_type_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("rev_"))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    geographic_unit_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("geographic_units.geographic_unit_id"))
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    default_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(8), default="XAF")


class PaymentChannel(Base, TimestampMixin, StatusMixin):
    __tablename__ = "payment_channels"

    payment_channel_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("pch_"))
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))


class FinancialPeriod(Base, TimestampMixin, StatusMixin):
    __tablename__ = "financial_periods"

    financial_period_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("fp_"))
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tenants.tenant_id"), index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    period_type: Mapped[str] = mapped_column(String(32), default="YEAR")  # YEAR | MONTH | QUARTER
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class FeeConfiguration(Base, TimestampMixin, StatusMixin):
    __tablename__ = "fee_configurations"

    fee_configuration_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("fee_"))
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tenants.tenant_id"), index=True)
    geographic_unit_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("geographic_units.geographic_unit_id"))
    revenue_type_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("revenue_types.revenue_type_id"))
    payment_channel_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("payment_channels.payment_channel_id"))
    fee_type: Mapped[str] = mapped_column(String(32), default="FLAT")  # FLAT | PERCENT
    fee_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(8), default="XAF")
    effective_from: Mapped[Optional[datetime]] = mapped_column(DateTime)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime)


class FeeBand(Base, TimestampMixin):
    __tablename__ = "fee_bands"

    fee_band_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("fbd_"))
    fee_configuration_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fee_configurations.fee_configuration_id"), nullable=False, index=True
    )
    min_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    max_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    fee_type: Mapped[str] = mapped_column(String(32), default="FLAT")
    fee_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)


class CommissionAgreement(Base, TimestampMixin, StatusMixin):
    __tablename__ = "commission_agreements"

    commission_agreement_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("com_"))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    revenue_type_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("revenue_types.revenue_type_id"))
    payment_channel_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("payment_channels.payment_channel_id"))
    commission_type: Mapped[str] = mapped_column(String(32), default="PERCENT")
    commission_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    effective_from: Mapped[Optional[datetime]] = mapped_column(DateTime)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime)
