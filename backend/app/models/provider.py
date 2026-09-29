from typing import Optional

from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_id


class ProviderConfiguration(Base, TimestampMixin):
    """Platform-level integration credentials; secrets stored encrypted."""

    __tablename__ = "provider_configurations"
    __table_args__ = (UniqueConstraint("provider_code", name="uq_provider_code"),)

    provider_config_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("pvc_"))
    provider_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    # Fernet-encrypted JSON blob of credentials / settings
    encrypted_payload: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Non-secret display hints (environment, base_url host, etc.)
    public_meta: Mapped[Optional[str]] = mapped_column(Text)
    updated_by: Mapped[Optional[str]] = mapped_column(String(36))


class ProviderPaymentIntent(Base, TimestampMixin):
    """Tracks Campay (or other) provider operations linked to EasyPay entities."""

    __tablename__ = "provider_payment_intents"

    intent_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("ppi_"))
    provider_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # COLLECT | WITHDRAW | DISBURSE | BANK_TRANSFER
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    amount: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="XAF")
    destination: Mapped[Optional[str]] = mapped_column(String(128))
    provider_reference: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    external_reference: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    payout_method: Mapped[Optional[str]] = mapped_column(String(32))
    # MOMO | BANK
    raw_response: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
