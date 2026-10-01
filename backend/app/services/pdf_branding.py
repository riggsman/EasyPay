"""Shared PDF branding: washed logo watermark + verification QR codes.

Watermarks are drawn in ``beforePage`` so they sit *under* page content and
never overprint / wash out receipt text.
"""
from __future__ import annotations

from io import BytesIO
from typing import Callable, Optional

import qrcode
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Image as RLImage, Paragraph, SimpleDocTemplate, Table, TableStyle
from sqlalchemy.orm import Session

from app.services.branding import (
    public_verify_url,
    resolve_logo_file,
    washed_logo_png,
)


def _draw_centered_watermark(canvas, pagesize, reader: ImageReader) -> None:
    canvas.saveState()
    page_w, page_h = pagesize
    # Opaque white base so the wash never tints through transparent flowables
    canvas.setFillColor(colors.white)
    canvas.rect(0, 0, page_w, page_h, fill=1, stroke=0)
    max_w, max_h = page_w * 0.55, page_h * 0.55
    iw, ih = reader.getSize()
    if not iw or not ih:
        canvas.restoreState()
        return
    scale = min(max_w / iw, max_h / ih)
    w, h = iw * scale, ih * scale
    x = (page_w - w) / 2.0
    y = (page_h - h) / 2.0
    # mask="auto" respects PNG alpha; drawn from beforePage so text paints on top
    canvas.drawImage(reader, x, y, width=w, height=h, mask="auto", preserveAspectRatio=True)
    canvas.restoreState()


def attach_logo_watermark(
    doc: SimpleDocTemplate,
    db: Session,
    *,
    tenant_id: Optional[str] = None,
    force_platform: bool = False,
) -> None:
    """Attach a washed logo that paints *before* flowables (behind all text)."""
    path = resolve_logo_file(db, tenant_id=tenant_id, force_platform=force_platform)
    reader: Optional[ImageReader] = None
    if path:
        try:
            reader = ImageReader(BytesIO(washed_logo_png(path)))
        except Exception:  # noqa: BLE001
            reader = None

    if not reader:
        return

    previous = getattr(doc, "beforePage", None)

    def before_page() -> None:
        _draw_centered_watermark(doc.canv, doc.pagesize, reader)
        if callable(previous):
            previous()

    doc.beforePage = before_page  # type: ignore[method-assign]


def logo_watermark_callbacks(
    db: Session,
    *,
    tenant_id: Optional[str] = None,
    force_platform: bool = False,
) -> Callable[[SimpleDocTemplate], None]:
    """Return a callable that attaches the under-text logo watermark to a doc."""

    def _attach(doc: SimpleDocTemplate) -> None:
        attach_logo_watermark(
            doc,
            db,
            tenant_id=tenant_id,
            force_platform=force_platform,
        )

    return _attach


def build_qr_png(url: str) -> bytes:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=1,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#14231c", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def qr_flowable(url: str, size_mm: float = 28) -> RLImage:
    return RLImage(BytesIO(build_qr_png(url)), width=size_mm * mm, height=size_mm * mm)


def verification_block(
    *,
    verification_token: str,
    styles: dict,
) -> list:
    """QR + human-readable code; verification still uses the same token endpoints."""
    url = public_verify_url(verification_token)
    hint = ParagraphStyle(
        "VerifyHint",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.black,
        leading=11,
    )
    code_style = ParagraphStyle(
        "VerifyCode",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.black,
        leading=12,
    )
    text = Paragraph(
        "<b>Scan to verify</b><br/>"
        "Scan the QR code or enter the verification code below. "
        "Revoked receipts will not verify.<br/><br/>"
        f"<b>Verification code:</b> {verification_token or '—'}",
        hint,
    )
    # Override with slightly larger leading for the mixed block
    text.style = ParagraphStyle(
        "VerifyBlock",
        parent=code_style,
        fontSize=9,
        leading=12,
        textColor=colors.black,
    )
    qr = qr_flowable(url, size_mm=30)
    table = Table([[text, qr]], colWidths=[130 * mm, 36 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return [table]
