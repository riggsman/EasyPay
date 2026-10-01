"""Payer transaction-history export with free allowance + charged downloads."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Optional

from fastapi import HTTPException
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.db.base import new_id, utcnow
from app.models.config import SystemConfiguration
from app.models.history_export import HistoryExport
from app.models.payer import Payer
from app.models.transaction import Transaction
from app.services.providers.campay import CampayClient, record_intent

CONFIG_FEE = "exports.history.fee_amount"
CONFIG_FREE = "exports.history.free_downloads"
CONFIG_CURRENCY = "exports.history.currency"

DEFAULT_FEE = Decimal("500")
DEFAULT_FREE = 2
DEFAULT_CURRENCY = "XAF"


def _config_value(db: Session, key: str) -> Optional[str]:
    row = (
        db.query(SystemConfiguration)
        .filter(SystemConfiguration.config_key == key, SystemConfiguration.tenant_id.is_(None))
        .first()
    )
    return row.config_value if row else None


def upsert_platform_config(db: Session, key: str, value: str, description: str) -> SystemConfiguration:
    row = (
        db.query(SystemConfiguration)
        .filter(SystemConfiguration.config_key == key, SystemConfiguration.tenant_id.is_(None))
        .first()
    )
    if row:
        row.config_value = value
        row.description = description
    else:
        row = SystemConfiguration(
            tenant_id=None,
            config_key=key,
            config_value=value,
            description=description,
        )
        db.add(row)
    db.flush()
    return row


def get_history_export_settings(db: Session) -> dict:
    fee_raw = _config_value(db, CONFIG_FEE)
    free_raw = _config_value(db, CONFIG_FREE)
    currency = _config_value(db, CONFIG_CURRENCY) or DEFAULT_CURRENCY
    try:
        fee = Decimal(fee_raw) if fee_raw is not None else DEFAULT_FEE
    except (InvalidOperation, TypeError):
        fee = DEFAULT_FEE
    try:
        free_downloads = int(free_raw) if free_raw is not None else DEFAULT_FREE
    except (TypeError, ValueError):
        free_downloads = DEFAULT_FREE
    if fee < 0:
        fee = DEFAULT_FEE
    if free_downloads < 0:
        free_downloads = 0
    return {
        "fee_amount": fee,
        "free_downloads": free_downloads,
        "currency": currency,
    }


def ensure_default_history_export_settings(db: Session) -> dict:
    settings = get_history_export_settings(db)
    if _config_value(db, CONFIG_FEE) is None:
        upsert_platform_config(db, CONFIG_FEE, str(DEFAULT_FEE), "Fee charged after free transaction-history downloads")
    if _config_value(db, CONFIG_FREE) is None:
        upsert_platform_config(db, CONFIG_FREE, str(DEFAULT_FREE), "Number of free transaction-history downloads per payer")
    if _config_value(db, CONFIG_CURRENCY) is None:
        upsert_platform_config(db, CONFIG_CURRENCY, DEFAULT_CURRENCY, "Currency for history export fee")
    db.commit()
    return get_history_export_settings(db)


def update_history_export_settings(db: Session, *, fee_amount: Decimal, free_downloads: int, currency: str = "XAF") -> dict:
    if fee_amount < 0:
        raise HTTPException(status_code=422, detail="fee_amount must be >= 0")
    if free_downloads < 0:
        raise HTTPException(status_code=422, detail="free_downloads must be >= 0")
    upsert_platform_config(db, CONFIG_FEE, str(fee_amount), "Fee charged after free transaction-history downloads")
    upsert_platform_config(db, CONFIG_FREE, str(int(free_downloads)), "Number of free transaction-history downloads per payer")
    upsert_platform_config(db, CONFIG_CURRENCY, (currency or DEFAULT_CURRENCY).upper(), "Currency for history export fee")
    db.commit()
    return get_history_export_settings(db)


def count_free_exports(db: Session, payer_id: str) -> int:
    return (
        db.query(HistoryExport)
        .filter(
            HistoryExport.payer_id == payer_id,
            HistoryExport.was_free.is_(True),
            HistoryExport.status == "COMPLETED",
        )
        .count()
    )


def quote_history_export(db: Session, payer: Payer) -> dict:
    settings = get_history_export_settings(db)
    used = count_free_exports(db, payer.payer_id)
    allowance = settings["free_downloads"]
    remaining = max(allowance - used, 0)
    will_charge = remaining <= 0
    return {
        "fee_amount": settings["fee_amount"],
        "currency": settings["currency"],
        "free_downloads": allowance,
        "free_downloads_used": used,
        "free_downloads_remaining": remaining,
        "will_charge": will_charge,
        "charge_amount": settings["fee_amount"] if will_charge else Decimal("0"),
    }


def _parse_bounds(date_from: datetime, date_to: datetime) -> tuple[datetime, datetime]:
    if date_from.tzinfo:
        date_from = date_from.replace(tzinfo=None)
    if date_to.tzinfo:
        date_to = date_to.replace(tzinfo=None)
    if date_to < date_from:
        raise HTTPException(status_code=422, detail="date_to must be on or after date_from")
    # inclusive end-of-day if time is midnight
    if date_to.hour == 0 and date_to.minute == 0 and date_to.second == 0 and date_to.microsecond == 0:
        date_to = date_to.replace(hour=23, minute=59, second=59)
    return date_from, date_to


def _load_transactions(db: Session, payer_id: str, date_from: datetime, date_to: datetime) -> list[Transaction]:
    return (
        db.query(Transaction)
        .filter(
            Transaction.payer_id == payer_id,
            Transaction.initiated_at >= date_from,
            Transaction.initiated_at <= date_to,
        )
        .order_by(Transaction.initiated_at.asc())
        .all()
    )


def build_history_pdf(
    *,
    db: Session,
    payer: Payer,
    transactions: list[Transaction],
    date_from: datetime,
    date_to: datetime,
    quote: dict,
    force_platform: bool = False,
) -> bytes:
    from app.services.pdf_branding import logo_watermark_callbacks

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="EasyPay Transaction History",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "HistTitle",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=colors.HexColor("#134832"),
        spaceAfter=4,
    )
    meta = ParagraphStyle(
        "HistMeta",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#4a5c52"),
        spaceAfter=8,
    )
    payer_name = payer.business_name or payer.full_name or payer.payer_reference
    story = [
        Paragraph("EasyPay — Transaction History", title),
        Paragraph(
            f"Payer: {payer_name} ({payer.payer_reference}) · "
            f"Period: {date_from.strftime('%Y-%m-%d')} → {date_to.strftime('%Y-%m-%d')} · "
            f"Generated: {utcnow().strftime('%Y-%m-%d %H:%M UTC')} · "
            + (
                "Free download"
                if not quote["will_charge"]
                else f"Charged {quote['fee_amount']} {quote['currency']}"
            ),
            meta,
        ),
        Spacer(1, 4),
    ]
    header = ["Reference", "Date", "Channel", "Status", "Amount", "Fee", "Total", "Currency"]
    rows = [header]
    for t in transactions:
        rows.append(
            [
                t.transaction_reference,
                t.initiated_at.strftime("%Y-%m-%d %H:%M") if t.initiated_at else "—",
                t.payment_channel or "—",
                t.status or "—",
                f"{t.amount:,.2f}",
                f"{t.service_fee:,.2f}",
                f"{t.total_amount:,.2f}",
                t.currency or "XAF",
            ]
        )
    if len(rows) == 1:
        rows.append(["—", "No transactions in this period", "", "", "", "", "", ""])
    table = Table(rows, colWidths=[38 * mm, 32 * mm, 28 * mm, 24 * mm, 28 * mm, 24 * mm, 28 * mm, 22 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#134832")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c5d6cc")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#edf5f0")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            f"Total rows: {len(transactions)}. Free downloads remaining after this export are managed by platform policy.",
            meta,
        )
    )
    attach = logo_watermark_callbacks(
        db,
        tenant_id=None if force_platform else payer.tenant_id,
        force_platform=force_platform,
    )
    attach(doc)
    doc.build(story)
    return buffer.getvalue()


def _charge_export_fee(db: Session, *, payer: Payer, amount: Decimal, currency: str, phone: str, export_ref: str) -> str:
    if not phone:
        raise HTTPException(status_code=422, detail="phone_number required to charge history export fee via Mobile Money")
    client = CampayClient(db)
    result = client.collect(
        amount=amount,
        phone=phone,
        description=f"EasyPay history export fee {export_ref}",
        external_reference=export_ref,
        currency=currency,
    )
    record_intent(
        db,
        operation="COLLECT",
        entity_type="history_export",
        entity_id=export_ref,
        tenant_id=payer.tenant_id,
        amount=str(amount),
        currency=currency,
        destination=phone,
        result=result,
        external_reference=export_ref,
        payout_method="MOMO",
    )
    if not result.ok or not result.reference:
        raise HTTPException(status_code=402, detail=result.error or "Fee collection failed")
    status = client.get_transaction_status(result.reference)
    ok_statuses = {"SUCCESSFUL", "SUCCESS", "COMPLETED"}
    status_code = (status.status or "").upper()
    if status_code not in ok_statuses:
        if client.mock and status_code in ok_statuses | {"PENDING"}:
            return result.reference
        raise HTTPException(status_code=402, detail=f"Fee payment not successful ({status.status})")
    return result.reference


def generate_history_export(
    db: Session,
    *,
    payer: Payer,
    user_id: str,
    date_from: datetime,
    date_to: datetime,
    phone_number: Optional[str] = None,
) -> tuple[bytes, HistoryExport, dict]:
    date_from, date_to = _parse_bounds(date_from, date_to)
    quote = quote_history_export(db, payer)
    transactions = _load_transactions(db, payer.payer_id, date_from, date_to)
    export_ref = new_id("hx_")  # keep short for provider_payment_intents.entity_id
    was_free = not quote["will_charge"]
    fee_amount = quote["charge_amount"]
    provider_reference = None
    phone = phone_number or payer.phone_number

    if not was_free:
        try:
            provider_reference = _charge_export_fee(
                db,
                payer=payer,
                amount=fee_amount,
                currency=quote["currency"],
                phone=phone or "",
                export_ref=export_ref,
            )
        except HTTPException as exc:
            row = HistoryExport(
                payer_id=payer.payer_id,
                user_id=user_id,
                tenant_id=payer.tenant_id,
                date_from=date_from,
                date_to=date_to,
                was_free=False,
                fee_amount=fee_amount,
                currency=quote["currency"],
                transaction_count=len(transactions),
                phone_number=phone,
                status="CHARGE_FAILED",
                note=str(exc.detail),
            )
            db.add(row)
            db.commit()
            raise

    pdf = build_history_pdf(
        db=db,
        payer=payer,
        transactions=transactions,
        date_from=date_from,
        date_to=date_to,
        quote=quote,
        force_platform=False,
    )
    row = HistoryExport(
        payer_id=payer.payer_id,
        user_id=user_id,
        tenant_id=payer.tenant_id,
        date_from=date_from,
        date_to=date_to,
        was_free=was_free,
        fee_amount=fee_amount if not was_free else Decimal("0"),
        currency=quote["currency"],
        transaction_count=len(transactions),
        phone_number=phone if not was_free else None,
        provider_reference=provider_reference,
        status="COMPLETED",
        note="Free allowance used" if was_free else "Fee charged via Campay",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    # Refresh quote after recording
    after = quote_history_export(db, payer)
    return pdf, row, after
