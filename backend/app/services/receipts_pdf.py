"""Generate official EasyPay receipt PDFs."""
from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.receipt import Receipt


def receipt_pdf_path(receipt_id: str) -> str:
    return f"/api/v1/receipts/{receipt_id}/pdf"


def build_receipt_pdf(receipt: Receipt) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"EasyPay Receipt {receipt.receipt_number}",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "EasyPayTitle",
        parent=styles["Heading1"],
        fontSize=20,
        textColor=colors.HexColor("#134832"),
        spaceAfter=4,
    )
    subtitle = ParagraphStyle(
        "EasyPaySubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#4a5c52"),
        spaceAfter=14,
    )
    label = ParagraphStyle(
        "EasyPayLabel",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#5b6b62"),
    )
    value = ParagraphStyle(
        "EasyPayValue",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#14231c"),
        spaceAfter=6,
    )

    currency = receipt.currency or "XAF"
    payment_date = receipt.payment_date.strftime("%Y-%m-%d %H:%M UTC") if receipt.payment_date else "—"
    rows = [
        ["Receipt number", receipt.receipt_number],
        ["Status", receipt.status or "ISSUED"],
        ["Council", receipt.council_name or "—"],
        ["Payer", receipt.payer_display_name or "—"],
        ["Revenue", receipt.revenue_name or "—"],
        ["Payment channel", receipt.payment_channel or "—"],
        ["Payment date", payment_date],
        ["Amount", f"{receipt.amount:,.2f} {currency}"],
        ["Service fee", f"{receipt.service_fee:,.2f} {currency}"],
        ["Total paid", f"{receipt.total_amount:,.2f} {currency}"],
        ["Verification code", receipt.verification_token or "—"],
    ]
    table = Table(rows, colWidths=[45 * mm, 120 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#edf5f0")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#14231c")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, -2), (1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c5d6cc")),
                ("BACKGROUND", (0, -2), (-1, -2), colors.HexColor("#dff0e6")),
            ]
        )
    )

    story = [
        Paragraph("EasyPay", title),
        Paragraph("Official council levy payment receipt", subtitle),
        Paragraph("This document confirms a settled payment recorded by EasyPay.", label),
        Spacer(1, 8),
        table,
        Spacer(1, 14),
        Paragraph(
            "Verify authenticity with the receipt number or verification code on the EasyPay verify page.",
            value,
        ),
    ]
    doc.build(story)
    return buffer.getvalue()
