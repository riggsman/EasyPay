from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, StatusMixin, new_id


class Payer(Base, TimestampMixin, StatusMixin):
    __tablename__ = "payers"

    payer_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("pay_"))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.user_id"), unique=True, nullable=False)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tenants.tenant_id"), index=True)
    payer_reference: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    payer_type: Mapped[str] = mapped_column(String(64), default="INDIVIDUAL")
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_name: Mapped[Optional[str]] = mapped_column(String(255))
    identification_type: Mapped[Optional[str]] = mapped_column(String(64))
    identification_number: Mapped[Optional[str]] = mapped_column(String(128))
    date_of_birth: Mapped[Optional[str]] = mapped_column(String(32))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone_number: Mapped[Optional[str]] = mapped_column(String(64))
    address: Mapped[Optional[str]] = mapped_column(Text)
    current_geographic_unit_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("geographic_units.geographic_unit_id"), index=True
    )


class PayerGeographicHistory(Base, TimestampMixin, StatusMixin):
    __tablename__ = "payer_geographic_history"

    payer_geographic_history_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: new_id("pgh_")
    )
    payer_id: Mapped[str] = mapped_column(String(36), ForeignKey("payers.payer_id"), nullable=False, index=True)
    geographic_unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("geographic_units.geographic_unit_id"), nullable=False, index=True
    )
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tenants.tenant_id"), index=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime)
    change_reason: Mapped[Optional[str]] = mapped_column(Text)
    change_source: Mapped[str] = mapped_column(String(64), default="REGISTRATION")
    changed_by: Mapped[Optional[str]] = mapped_column(String(36))


class ZoneChangeRequest(Base, TimestampMixin, StatusMixin):
    __tablename__ = "zone_change_requests"

    zone_change_request_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("zcr_"))
    payer_id: Mapped[str] = mapped_column(String(36), ForeignKey("payers.payer_id"), nullable=False, index=True)
    from_geographic_unit_id: Mapped[str] = mapped_column(String(36), ForeignKey("geographic_units.geographic_unit_id"))
    to_geographic_unit_id: Mapped[str] = mapped_column(String(36), ForeignKey("geographic_units.geographic_unit_id"))
    from_tenant_id: Mapped[Optional[str]] = mapped_column(String(36))
    to_tenant_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(36))
    review_notes: Mapped[Optional[str]] = mapped_column(Text)
    # status: PENDING | UNDER_REVIEW | APPROVED | REJECTED
