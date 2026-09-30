from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, StatusMixin, new_id


class Platform(Base, TimestampMixin, StatusMixin):
    __tablename__ = "platforms"

    platform_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("plt_"))
    platform_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    platform_name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[Optional[str]] = mapped_column(String(255))
    registration_number: Mapped[Optional[str]] = mapped_column(String(128))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(64))
    address: Mapped[Optional[str]] = mapped_column(Text)
    default_currency: Mapped[str] = mapped_column(String(8), default="XAF", nullable=False)
    # Relative path under LOGO_STORAGE_DIR (e.g. platform/easypay-default.png)
    logo_path: Mapped[Optional[str]] = mapped_column(String(512))
