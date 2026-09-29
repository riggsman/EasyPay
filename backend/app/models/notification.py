from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_id


class NotificationDelivery(Base, TimestampMixin):
    __tablename__ = "notification_deliveries"

    notification_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("ntf_"))
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    channel: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(255))
    body_preview: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    entity_type: Mapped[Optional[str]] = mapped_column(String(64))
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
