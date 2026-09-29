from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, StatusMixin, new_id


class Obligation(Base, TimestampMixin, StatusMixin):
    __tablename__ = "obligations"

    obligation_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("obl_"))
    payer_id: Mapped[str] = mapped_column(String(36), ForeignKey("payers.payer_id"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    geographic_unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("geographic_units.geographic_unit_id"), nullable=False, index=True
    )
    revenue_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("revenue_types.revenue_type_id"), nullable=False)
    financial_period_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("financial_periods.financial_period_id"))
    description: Mapped[Optional[str]] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="XAF")
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # status: DUE | PARTIAL | PAID | CANCELLED | WAIVED
