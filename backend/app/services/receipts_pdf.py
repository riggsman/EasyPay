"""Official EasyPay receipt PDFs — classic invoice-style template adapted for the platform.

Template structure (from create_receipt_pdf):
  logo (left) + RECEIPT title / number / date (right)
  Bill To (payer) + Paid To (business) — no ship-to
  line items table (qty / description / unit / amount)
  sub-total, service fee, grand total
  terms + verification QR
  EasyPay footer brand mark
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Optional, Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.geography import GeographicUnit
from app.models.payer import Payer
from app.models.receipt import Receipt
from app.models.tenant import Tenant
from app.services.branding import absolute_logo_path, public_verify_url, resolve_logo_file
from app.services.pdf_branding import logo_watermark_callbacks, qr_flowable

# Template palette — clean invoice look, EasyPay green accents
_INK = colors.HexColor("#14231c")
_MUTED = colors.HexColor("#5b6b62")
_BLACK = colors.black
_RULE = colors.HexColor("#c5d6cc")
_BAND = colors.HexColor("#134832")
_BAND_SOFT = colors.HexColor("#edf5f0")
_TOTAL_BAND = colors.HexColor("#dff0e6")
_WHITE = colors.white


def receipt_pdf_path(receipt_id: str) -> str:
    return f"/api/v1/receipts/{receipt_id}/pdf"


def _money(value: float | int, currency: str) -> str:
    return f"{float(value):,.2f} {currency}"


def _footer_brand(label: Optional[str] = None) -> str:
    """Public footer mark — EasyPay only (never localhost / verify URLs)."""
    text = (label or "EasyPay").strip()
    if not text or "localhost" in text.lower() or "://" in text:
        return "EASYPAY"
    return text.upper()


def _header_logo_flowable(logo_path: Optional[Path], logo_text: str = "LOGO") -> object:
    if logo_path and logo_path.is_file():
        try:
            # Full-opacity header mark (wash is reserved for background watermark)
            return RLImage(str(logo_path), width=28 * mm, height=28 * mm, kind="proportional")
        except Exception:  # noqa: BLE001
            pass
    styles = getSampleStyleSheet()
    return Paragraph(
        f"<b>{logo_text}</b>",
        ParagraphStyle(
            "LogoText",
            parent=styles["Normal"],
            fontSize=16,
            textColor=_BAND,
            leading=20,
        ),
    )


def create_receipt_pdf(
    *,
    output_path: Optional[str] = None,
    receipt_no: str,
    receipt_date: str,
    logo_text: str = "EasyPay",
    logo_path: Optional[Path] = None,
    bill_to_name: str,
    bill_to_address: str = "",
    paid_to_name: str = "",
    paid_to_address: str = "",
    items: Sequence[dict],
    sub_total: float = 0.0,
    service_fee: float = 0.0,
    grand_total: float = 0.0,
    currency: str = "XAF",
    payment_channel: str = "",
    status: str = "ISSUED",
    terms_text: str = "",
    website: Optional[str] = None,
    verification_token: str = "",
    watermark_callbacks: Optional[tuple] = None,
) -> bytes:
    """Render the classic receipt template with EasyPay-relevant fields only.

    Stripped vs commercial invoice templates: no ship-to, no sales-tax label
    (service fee instead), no product SKUs — levy/payment lines only.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"EasyPay Receipt {receipt_no}",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "RcptTitle",
        parent=styles["Heading1"],
        fontSize=28,
        leading=32,
        textColor=_BAND,
        alignment=2,  # right
        spaceAfter=2,
    )
    meta_right = ParagraphStyle(
        "RcptMetaRight",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=_MUTED,
        alignment=2,
    )
    section_label = ParagraphStyle(
        "RcptSection",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
        textColor=_BAND,
        fontName="Helvetica-Bold",
        spaceAfter=2,
    )
    body = ParagraphStyle(
        "RcptBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=13,
        textColor=_INK,
    )
    small = ParagraphStyle(
        "RcptSmall",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        textColor=_MUTED,
    )
    terms_style = ParagraphStyle(
        "RcptTerms",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        textColor=_BLACK,
    )
    website_style = ParagraphStyle(
        "RcptWeb",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=_BAND,
        alignment=1,
        fontName="Helvetica-Bold",
    )

    logo = _header_logo_flowable(logo_path, logo_text=logo_text)
    header_right = [
        Paragraph("RECEIPT", title_style),
        Paragraph(f"<b>Receipt No:</b> {receipt_no}", meta_right),
        Paragraph(f"<b>Date:</b> {receipt_date}", meta_right),
        Paragraph(f"<b>Status:</b> {status}", meta_right),
    ]
    if payment_channel:
        header_right.append(Paragraph(f"<b>Channel:</b> {payment_channel}", meta_right))

    header = Table(
        [[logo, header_right]],
        colWidths=[70 * mm, 108 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    bill_block = [
        Paragraph("BILL TO", section_label),
        Paragraph(bill_to_name or "—", body),
    ]
    for line in (bill_to_address or "").split("\n"):
        if line.strip():
            bill_block.append(Paragraph(line.strip(), small))

    paid_block = [
        Paragraph("PAID TO", section_label),
        Paragraph(paid_to_name or "—", body),
    ]
    for line in (paid_to_address or "").split("\n"):
        if line.strip():
            paid_block.append(Paragraph(line.strip(), small))

    parties = Table([[bill_block, paid_block]], colWidths=[89 * mm, 89 * mm])
    parties.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, -1), _BAND_SOFT),
                ("BOX", (0, 0), (-1, -1), 0.5, _RULE),
                ("LINEAFTER", (0, 0), (0, 0), 0.5, _RULE),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    item_rows = [["QTY", "DESCRIPTION", "UNIT PRICE", "AMOUNT"]]
    for item in items:
        qty = item.get("qty", 1)
        desc = str(item.get("description") or "—")
        price = float(item.get("price") or 0)
        amount = float(item.get("amount") if item.get("amount") is not None else price * float(qty or 0))
        item_rows.append(
            [
                str(qty),
                Paragraph(desc, body),
                _money(price, currency),
                _money(amount, currency),
            ]
        )
    if len(item_rows) == 1:
        item_rows.append(["—", Paragraph("No line items", body), "—", "—"])

    items_table = Table(item_rows, colWidths=[18 * mm, 90 * mm, 35 * mm, 35 * mm])
    items_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _BAND),
                ("TEXTCOLOR", (0, 0), (-1, 0), _WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("TEXTCOLOR", (0, 1), (-1, -1), _INK),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.4, _RULE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_WHITE, _BAND_SOFT]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    totals_rows = [
        ["Sub Total", _money(sub_total, currency)],
        ["Service Fee", _money(service_fee, currency)],
        ["Grand Total", _money(grand_total, currency)],
    ]
    totals = Table(totals_rows, colWidths=[35 * mm, 40 * mm])
    totals.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (-1, -1), _INK),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("BACKGROUND", (0, -1), (-1, -1), _TOTAL_BAND),
                ("BOX", (0, 0), (-1, -1), 0.4, _RULE),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, _RULE),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    totals_wrap = Table([["", totals]], colWidths=[103 * mm, 75 * mm])
    totals_wrap.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    default_terms = (
        "This receipt confirms a settled payment recorded by EasyPay. "
        "Verify authenticity by scanning the QR code or entering the receipt number / "
        "verification code. Revoked receipts will not verify."
    )
    terms = terms_text or default_terms
    # QR still encodes the verify deep-link; never print the URL (avoids localhost in PDFs).
    verify_url = public_verify_url(verification_token) if verification_token else ""
    terms_left = [
        Paragraph("TERMS & VERIFICATION", section_label),
        Paragraph(terms, terms_style),
        Spacer(1, 4),
        Paragraph(f"<b>Verification code:</b> {verification_token or '—'}", body),
    ]
    qr = qr_flowable(verify_url, size_mm=28) if verification_token and verify_url else Spacer(1, 1)
    terms_table = Table([[terms_left, qr]], colWidths=[140 * mm, 38 * mm])
    terms_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )

    story = [
        header,
        Spacer(1, 4),
        HRFlowable(width="100%", thickness=1.2, color=_BAND, spaceBefore=2, spaceAfter=10),
        parties,
        Spacer(1, 12),
        items_table,
        Spacer(1, 10),
        totals_wrap,
        Spacer(1, 14),
        HRFlowable(width="100%", thickness=0.6, color=_RULE, spaceBefore=2, spaceAfter=8),
        terms_table,
        Spacer(1, 16),
        Paragraph(_footer_brand(website), website_style),
    ]

    if watermark_callbacks:
        on_first, on_later = watermark_callbacks
        doc.build(story, onFirstPage=on_first, onLaterPages=on_later)
    else:
        doc.build(story)
    pdf = buffer.getvalue()

    if output_path:
        Path(output_path).write_bytes(pdf)
    return pdf


def build_receipt_pdf(db: Session, receipt: Receipt) -> bytes:
    """Map an EasyPay Receipt onto the classic template and render."""
    payer = db.get(Payer, receipt.payer_id)
    tenant = db.get(Tenant, receipt.tenant_id)
    geo = db.get(GeographicUnit, receipt.geographic_unit_id) if receipt.geographic_unit_id else None

    logo_file = resolve_logo_file(db, tenant_id=receipt.tenant_id, force_platform=False)
    # Prefer full-color header logo; watermark uses washed copy separately
    header_logo = absolute_logo_path(tenant.logo_path) if tenant and tenant.logo_path else None
    if not header_logo:
        header_logo = logo_file

    bill_lines = []
    if payer:
        if payer.payer_reference:
            bill_lines.append(f"Ref: {payer.payer_reference}")
        if payer.phone_number:
            bill_lines.append(payer.phone_number)
        if payer.address:
            bill_lines.append(payer.address)
        elif geo:
            bill_lines.append(geo.unit_name)
    bill_to_address = "\n".join(bill_lines)

    paid_lines = []
    if tenant:
        if tenant.tenant_code:
            paid_lines.append(tenant.tenant_code)
        if geo:
            paid_lines.append(geo.unit_name)
        if tenant.email:
            paid_lines.append(tenant.email)
        if tenant.phone_number:
            paid_lines.append(tenant.phone_number)
    paid_to_address = "\n".join(paid_lines)

    currency = receipt.currency or "XAF"
    amount = float(receipt.amount or 0)
    fee = float(receipt.service_fee or 0)
    total = float(receipt.total_amount or (amount + fee))
    items = [
        {
            "qty": 1,
            "description": receipt.revenue_name or "Payment",
            "price": amount,
            "amount": amount,
        }
    ]
    if fee:
        items.append(
            {
                "qty": 1,
                "description": "Service fee",
                "price": fee,
                "amount": fee,
            }
        )

    receipt_date = (
        receipt.payment_date.strftime("%d/%m/%y")
        if receipt.payment_date
        else "—"
    )

    settings = get_settings()
    return create_receipt_pdf(
        receipt_no=receipt.receipt_number,
        receipt_date=receipt_date,
        logo_text=settings.APP_NAME or "EasyPay",
        logo_path=header_logo,
        bill_to_name=receipt.payer_display_name or (payer.full_name if payer else "Payer"),
        bill_to_address=bill_to_address,
        paid_to_name=receipt.council_name or (tenant.organization_name if tenant else "EasyPay"),
        paid_to_address=paid_to_address,
        items=items,
        sub_total=amount,
        service_fee=fee,
        grand_total=total,
        currency=currency,
        payment_channel=(receipt.payment_channel or "").replace("_", " "),
        status=receipt.status or "ISSUED",
        terms_text=(
            "Official EasyPay receipt. Amounts are final for the settled payment shown. "
            "Scan the QR code or use the verification code to confirm authenticity. "
            "Revoked receipts return NOT VERIFIED."
        ),
        website=settings.APP_NAME or "EasyPay",
        verification_token=receipt.verification_token or "",
        watermark_callbacks=logo_watermark_callbacks(
            db,
            tenant_id=receipt.tenant_id,
            force_platform=False,
        ),
    )
