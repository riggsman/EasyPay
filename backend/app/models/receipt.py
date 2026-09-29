from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, StatusMixin, new_id, utcnow


class Receipt(Base, TimestampMixin, StatusMixin):
    __tablename__ = "receipts"

    receipt_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("rcp_"))
    receipt_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    verification_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.transaction_id"), unique=True, nullable=False)
    payer_id: Mapped[str] = mapped_column(String(36), ForeignKey("payers.payer_id"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    geographic_unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("geographic_units.geographic_unit_id"), nullable=False
    )
    revenue_type_id: Mapped[Optional[str]] = mapped_column(String(36))
    payer_display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    council_name: Mapped[str] = mapped_column(String(255), nullable=False)
    revenue_name: Mapped[Optional[str]] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    service_fee: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="XAF")
    payment_date: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    payment_channel: Mapped[Optional[str]] = mapped_column(String(64))
    # status: ISSUED | REVOKED
