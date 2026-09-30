from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, StatusMixin, new_id


class Tenant(Base, TimestampMixin, StatusMixin):
    __tablename__ = "tenants"

    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("tnt_"))
    tenant_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    organization_type: Mapped[str] = mapped_column(String(64), default="COUNCIL")
    organization_name: Mapped[str] = mapped_column(String(255), nullable=False)
    registration_number: Mapped[Optional[str]] = mapped_column(String(128))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone_number: Mapped[Optional[str]] = mapped_column(String(64))
    location: Mapped[Optional[str]] = mapped_column(Text)
    momo_number: Mapped[Optional[str]] = mapped_column(String(64))
    bank_account_number: Mapped[Optional[str]] = mapped_column(String(128))
    currency: Mapped[str] = mapped_column(String(8), default="XAF")
    verification: Mapped[str] = mapped_column(String(32), default="PENDING")
    zone_change_mode: Mapped[str] = mapped_column(String(32), default="IMMEDIATE")  # IMMEDIATE | APPROVAL_REQUIRED
    # Relative path under LOGO_STORAGE_DIR (e.g. tenants/{id}.png); PDF falls back to platform logo
    logo_path: Mapped[Optional[str]] = mapped_column(String(512))
