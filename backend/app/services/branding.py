"""Tenant / platform logo resolution and public verify URL helpers."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.platform import Platform
from app.models.tenant import Tenant

# Relative filenames stored in logo_path columns
PLATFORM_DEFAULT_FILENAME = "platform/easypay-default.png"


def logo_storage_root() -> Path:
    settings = get_settings()
    root = Path(settings.LOGO_STORAGE_DIR)
    if not root.is_absolute():
        # backend/ root (parent of app/)
        root = Path(__file__).resolve().parents[2] / root
    root.mkdir(parents=True, exist_ok=True)
    return root


def ensure_logo_schema(db: Session) -> None:
    """Idempotent additive columns for logo paths."""
    alters = [
        "ALTER TABLE platforms ADD COLUMN logo_path VARCHAR(512) NULL",
        "ALTER TABLE tenants ADD COLUMN logo_path VARCHAR(512) NULL",
    ]
    for stmt in alters:
        try:
            db.execute(text(stmt))
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()


def public_base_url() -> str:
    """Frontend / public site base URL from config (no trailing slash)."""
    return get_settings().PUBLIC_BASE_URL.rstrip("/")


def public_verify_url(verification_token: str) -> str:
    """QR / deep-link URL for receipt verification. Uses opaque token only."""
    token = (verification_token or "").strip()
    if not token:
        return f"{public_base_url()}/verify"
    # Plan: encode /v/{opaque-token} — never amounts/ids in the query string
    return f"{public_base_url()}/v/{token}"


def absolute_logo_path(relative_or_absolute: Optional[str]) -> Optional[Path]:
    if not relative_or_absolute:
        return None
    path = Path(relative_or_absolute)
    if not path.is_absolute():
        path = logo_storage_root() / path
    return path if path.is_file() else None


def _write_default_platform_logo(dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", (512, 512), (19, 72, 50, 255))
    draw = ImageDraw.Draw(img)
    # Soft ring
    draw.ellipse((48, 48, 464, 464), outline=(223, 240, 230, 255), width=18)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 160)
    except OSError:
        font = ImageFont.load_default()
    text = "EP"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((512 - tw) / 2, (512 - th) / 2 - 8), text, fill=(255, 255, 255, 255), font=font)
    img.save(dest, format="PNG")


def ensure_default_platform_logo(db: Session) -> Path:
    """Ensure a platform logo file exists and is linked on the Platform row."""
    ensure_logo_schema(db)
    dest = logo_storage_root() / PLATFORM_DEFAULT_FILENAME
    if not dest.is_file():
        _write_default_platform_logo(dest)

    platform = db.query(Platform).order_by(Platform.created_at.asc()).first()
    if platform:
        if not platform.logo_path or not absolute_logo_path(platform.logo_path):
            platform.logo_path = PLATFORM_DEFAULT_FILENAME
            db.commit()
            db.refresh(platform)
    return dest


def resolve_logo_file(
    db: Session,
    *,
    tenant_id: Optional[str] = None,
    force_platform: bool = False,
) -> Optional[Path]:
    """Resolve logo for PDF branding.

    - Platform PDFs (`force_platform`): platform logo (default generated if missing)
    - Tenant PDFs: tenant logo, else platform logo fallback
    """
    ensure_default_platform_logo(db)

    if not force_platform and tenant_id:
        tenant = db.get(Tenant, tenant_id)
        if tenant and tenant.logo_path:
            path = absolute_logo_path(tenant.logo_path)
            if path:
                return path

    platform = db.query(Platform).order_by(Platform.created_at.asc()).first()
    if platform and platform.logo_path:
        path = absolute_logo_path(platform.logo_path)
        if path:
            return path
    return absolute_logo_path(PLATFORM_DEFAULT_FILENAME)


def washed_logo_png(path: Path, wash_opacity: Optional[float] = None) -> bytes:
    """Return PNG bytes with alpha scaled to the configured wash opacity (default 60%)."""
    settings = get_settings()
    opacity = wash_opacity if wash_opacity is not None else float(settings.PDF_LOGO_WASH_OPACITY)
    opacity = max(0.05, min(1.0, opacity))
    img = Image.open(path).convert("RGBA")
    r, g, b, a = img.split()
    a = a.point(lambda p: int(p * opacity))
    out = Image.merge("RGBA", (r, g, b, a))
    buf = BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


def save_uploaded_logo(*, owner: str, owner_id: str, filename: str, data: bytes) -> str:
    """Persist an uploaded logo; returns relative path for DB storage."""
    rel = f"{owner}/{owner_id}.png"
    dest = logo_storage_root() / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Normalize to PNG with alpha for consistent watermarking
    img = Image.open(BytesIO(data)).convert("RGBA")
    img.save(dest, format="PNG")
    return rel
