from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_id


class AuditEvent(Base, TimestampMixin):
    __tablename__ = "audit_events"

    audit_event_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("aud_"))
    actor_user_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    before_json: Mapped[Optional[str]] = mapped_column(Text)
    after_json: Mapped[Optional[str]] = mapped_column(Text)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(64), default="API")
