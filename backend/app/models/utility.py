"""Platform utility / bill-pay service catalog and payment extras."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, StatusMixin, TimestampMixin, new_id


class UtilityService(Base, TimestampMixin, StatusMixin):
    """Catalog entry shown as a store card when status=ACTIVE."""

    __tablename__ = "utility_services"

    utility_service_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("usv_"))
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(64), default="UTILITY")  # ELECTRICITY | WATER | OTHER
    icon_key: Mapped[str] = mapped_column(String(64), default="bolt")
    accent_color: Mapped[str] = mapped_column(String(16), default="#1f6b4a")
    # Fee config (mirrors FeeConfiguration semantics for this service)
    fee_type: Mapped[str] = mapped_column(String(32), default="FLAT")  # FLAT | PERCENT
    fee_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("500"))
    currency: Mapped[str] = mapped_column(String(8), default="XAF")
    accept_meter_number: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    accept_bill_number: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    provider_hint: Mapped[Optional[str]] = mapped_column(String(128))
    # status: ACTIVE | DISABLED | INACTIVE


class UtilityPaymentDetail(Base, TimestampMixin):
    """Extra fields for a utility bill payment linked 1:1 to a transaction."""

    __tablename__ = "utility_payment_details"

    utility_payment_detail_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: new_id("upd_")
    )
    transaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("transactions.transaction_id"), unique=True, nullable=False, index=True
    )
    utility_service_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("utility_services.utility_service_id"), nullable=False, index=True
    )
    # Exactly one of meter_number / bill_number is set
    reference_type: Mapped[str] = mapped_column(String(16), nullable=False)  # METER | BILL
    meter_number: Mapped[Optional[str]] = mapped_column(String(64))
    bill_number: Mapped[Optional[str]] = mapped_column(String(64))
    account_label: Mapped[Optional[str]] = mapped_column(String(255))
    service_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    service_code_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    bill_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    receipt_emailed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
