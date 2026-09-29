from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, StatusMixin, new_id


class FinancialAccount(Base, TimestampMixin, StatusMixin):
    __tablename__ = "financial_accounts"

    financial_account_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("fac_"))
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tenants.tenant_id"), index=True)
    account_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(32), nullable=False)  # ASSET | LIABILITY | REVENUE | EXPENSE
    currency: Mapped[str] = mapped_column(String(8), default="XAF")


class LedgerPosting(Base, TimestampMixin):
    __tablename__ = "ledger_postings"

    ledger_posting_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("lpo_"))
    transaction_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("transactions.transaction_id"), index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    geographic_unit_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    posting_type: Mapped[str] = mapped_column(String(32), default="PAYMENT")  # PAYMENT | REVERSAL | ADJUSTMENT
    reversal_of_id: Mapped[Optional[str]] = mapped_column(String(36))


class LedgerEntry(Base, TimestampMixin):
    __tablename__ = "ledger_entries"

    ledger_entry_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("led_"))
    ledger_posting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ledger_postings.ledger_posting_id"), nullable=False, index=True
    )
    financial_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("financial_accounts.financial_account_id"), nullable=False, index=True
    )
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    geographic_unit_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    debit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    credit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(8), default="XAF")
    narrative: Mapped[Optional[str]] = mapped_column(String(255))
