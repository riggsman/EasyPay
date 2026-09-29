from typing import Optional

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_id


class SystemConfiguration(Base, TimestampMixin):
    __tablename__ = "system_configurations"
    __table_args__ = (UniqueConstraint("tenant_id", "config_key", name="uq_config_key"),)

    config_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("cfg_"))
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)  # null = platform-wide
    config_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    config_value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))
