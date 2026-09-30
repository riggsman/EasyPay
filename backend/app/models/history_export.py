from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_id


class HistoryExport(Base, TimestampMixin):
    """Record of a payer downloading their transaction history."""

    __tablename__ = "history_exports"

    export_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("hex_"))
    payer_id: Mapped[str] = mapped_column(String(36), ForeignKey("payers.payer_id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.user_id"), nullable=False, index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tenants.tenant_id"), index=True)
    date_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    date_to: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    was_free: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="XAF")
    transaction_count: Mapped[int] = mapped_column(Integer, default=0)
    phone_number: Mapped[Optional[str]] = mapped_column(String(32))
    provider_reference: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    # status: COMPLETED | FAILED | CHARGE_FAILED
    status: Mapped[str] = mapped_column(String(32), default="COMPLETED", nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text)
