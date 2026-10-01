"""Top-level payer payment products (council levies, utilities, future types)."""
from typing import Optional

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, StatusMixin, TimestampMixin, new_id


class PaymentProduct(Base, TimestampMixin, StatusMixin):
    """Chooser card on Make Payment. ACTIVE products are offered to payers.

    `route_path` points at the payer UI for that product. New products can be
    registered without hard-coding the chooser — disable to hide.
    """

    __tablename__ = "payment_products"

    payment_product_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("pp_"))
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    icon_key: Mapped[str] = mapped_column(String(64), default="wallet")
    accent_color: Mapped[str] = mapped_column(String(16), default="#1f6b4a")
    # Frontend route relative to payer portal, e.g. /payer/pay/council
    route_path: Mapped[str] = mapped_column(String(255), nullable=False)
    # When true, product is only shown if dependent catalog has ACTIVE items
    # (e.g. utilities require at least one active UtilityService)
    requires_catalog: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    catalog_type: Mapped[Optional[str]] = mapped_column(String(64))  # UTILITY | None
    sort_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    # status: ACTIVE | DISABLED
