from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_id


class PasswordResetChallenge(Base, TimestampMixin):
    """One-time password challenge for self-serve password reset."""

    __tablename__ = "password_reset_challenges"

    challenge_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("prc_"))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.user_id"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)  # EMAIL | SMS | WHATSAPP
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    otp_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False, index=True)
    # PENDING | VERIFIED | CONSUMED | EXPIRED | LOCKED
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
