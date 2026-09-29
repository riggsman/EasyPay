from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, StatusMixin, new_id


class GeographicUnit(Base, TimestampMixin, StatusMixin):
    __tablename__ = "geographic_units"

    geographic_unit_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("geo_"))
    parent_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("geographic_units.geographic_unit_id"), index=True)
    unit_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    unit_name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    country_code: Mapped[Optional[str]] = mapped_column(String(8))


class TenantGeographicUnit(Base, TimestampMixin, StatusMixin):
    __tablename__ = "tenant_geographic_units"
    __table_args__ = (UniqueConstraint("tenant_id", "geographic_unit_id", name="uq_tenant_geo"),)

    tenant_geographic_unit_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("tgu_"))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    geographic_unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("geographic_units.geographic_unit_id"), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(String(64), default="PRIMARY_COUNCIL")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)
    effective_from: Mapped[Optional[datetime]] = mapped_column(DateTime)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime)
