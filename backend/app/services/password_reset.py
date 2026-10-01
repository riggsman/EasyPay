"""Self-serve password reset via OTP (email / SMS / WhatsApp)."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_token, decode_token, hash_password
from app.db.base import utcnow
from app.models.password_reset import PasswordResetChallenge
from app.models.user import User
from app.services.audit import write_audit
from app.services.notifications import config as ncfg
from app.services.notifications.dispatcher import notify_password_reset_otp

OTP_LENGTH = 6
OTP_TTL_MINUTES = 10
RESET_TOKEN_TTL_MINUTES = 15
RESEND_COOLDOWN_SECONDS = 60
CHANNELS = ("EMAIL", "SMS", "WHATSAPP")


def _otp_hmac(otp: str) -> str:
    key = get_settings().SECRET_KEY.encode("utf-8")
    return hmac.new(key, otp.encode("utf-8"), hashlib.sha256).hexdigest()


def _generate_otp() -> str:
    upper = 10**OTP_LENGTH
    return f"{secrets.randbelow(upper):0{OTP_LENGTH}d}"


def mask_destination(channel: str, destination: str) -> str:
    if not destination:
        return ""
    if channel == "EMAIL":
        if "@" not in destination:
            return "***"
        local, _, domain = destination.partition("@")
        if len(local) <= 1:
            return f"*@{domain}"
        return f"{local[0]}***@{domain}"
    digits = re.sub(r"\D", "", destination)
    if len(digits) <= 4:
        return "***"
    return f"***{digits[-4:]}"


def find_user_by_identifier(db: Session, identifier: str) -> Optional[User]:
    ident = (identifier or "").strip()
    if not ident:
        return None
    return (
        db.query(User)
        .filter(
            or_(
                User.username == ident,
                User.email == ident,
                User.phone_number == ident,
            )
        )
        .first()
    )


def destination_for_channel(user: User, channel: str) -> Optional[str]:
    if channel == "EMAIL":
        return (user.email or "").strip() or None
    if channel in ("SMS", "WHATSAPP"):
        return (user.phone_number or "").strip() or None
    return None


def available_channels(db: Session, tenant_id: Optional[str] = None) -> dict:
    return {
        "email": ncfg.channel_enabled(db, tenant_id, "EMAIL"),
        "sms": ncfg.channel_enabled(db, tenant_id, "SMS"),
        "whatsapp": ncfg.channel_enabled(db, tenant_id, "WHATSAPP"),
        "otp_length": OTP_LENGTH,
        "otp_ttl_minutes": OTP_TTL_MINUTES,
    }


def request_otp(db: Session, *, identifier: str, channel: str) -> dict:
    channel = (channel or "").strip().upper()
    if channel not in CHANNELS:
        raise HTTPException(status_code=400, detail="Invalid channel. Use EMAIL, SMS, or WHATSAPP.")

    generic = {
        "message": "If an account matches, a one-time code was sent.",
        "challenge_id": None,
        "channel": channel,
        "destination_hint": None,
        "expires_in_seconds": OTP_TTL_MINUTES * 60,
    }

    user = find_user_by_identifier(db, identifier)
    if not user or not user.is_active:
        return generic

    if not ncfg.channel_enabled(db, user.tenant_id, channel):
        raise HTTPException(status_code=400, detail=f"{channel} delivery is currently unavailable.")

    destination = destination_for_channel(user, channel)
    if not destination:
        # Avoid leaking whether the account exists without that contact method.
        return generic

    now = utcnow()
    # Drop timed-out challenges so they do not block resend forever.
    for stale in (
        db.query(PasswordResetChallenge)
        .filter(
            PasswordResetChallenge.user_id == user.user_id,
            PasswordResetChallenge.status.in_(("PENDING", "VERIFIED")),
            PasswordResetChallenge.expires_at < now,
        )
        .all()
    ):
        stale.status = "EXPIRED"

    recent = (
        db.query(PasswordResetChallenge)
        .filter(
            PasswordResetChallenge.user_id == user.user_id,
            PasswordResetChallenge.status == "PENDING",
        )
        .order_by(PasswordResetChallenge.created_at.desc())
        .first()
    )
    if recent and (now - recent.created_at).total_seconds() < RESEND_COOLDOWN_SECONDS:
        raise HTTPException(
            status_code=429,
            detail=f"Please wait {RESEND_COOLDOWN_SECONDS} seconds before requesting another code.",
        )

    # Invalidate outstanding challenges for this user.
    for row in (
        db.query(PasswordResetChallenge)
        .filter(
            PasswordResetChallenge.user_id == user.user_id,
            PasswordResetChallenge.status.in_(("PENDING", "VERIFIED")),
        )
        .all()
    ):
        row.status = "EXPIRED"

    otp = _generate_otp()
    challenge = PasswordResetChallenge(
        user_id=user.user_id,
        channel=channel,
        destination=destination,
        otp_hash=_otp_hmac(otp),
        expires_at=utcnow() + timedelta(minutes=OTP_TTL_MINUTES),
        status="PENDING",
    )
    db.add(challenge)
    db.flush()

    delivery_status = notify_password_reset_otp(
        db,
        user=user,
        channel=channel,
        destination=destination,
        otp=otp,
        entity_id=challenge.challenge_id,
    )
    if delivery_status in ("FAILED", "SKIPPED"):
        challenge.status = "EXPIRED"
    write_audit(
        db,
        actor_user_id=user.user_id,
        tenant_id=user.tenant_id,
        entity_type="password_reset",
        entity_id=challenge.challenge_id,
        action="PASSWORD_RESET_REQUESTED",
        after={"channel": channel, "delivery_status": delivery_status},
    )
    db.commit()
    db.refresh(challenge)

    if delivery_status == "FAILED":
        raise HTTPException(status_code=502, detail="Could not send the one-time code. Try another channel.")
    if delivery_status == "SKIPPED":
        raise HTTPException(status_code=400, detail=f"{channel} delivery is currently unavailable.")

    return {
        "message": "If an account matches, a one-time code was sent.",
        "challenge_id": challenge.challenge_id,
        "channel": channel,
        "destination_hint": mask_destination(channel, destination),
        "expires_in_seconds": OTP_TTL_MINUTES * 60,
    }


def verify_otp(db: Session, *, challenge_id: str, otp: str) -> dict:
    challenge = db.get(PasswordResetChallenge, challenge_id)
    if not challenge or challenge.status not in ("PENDING", "VERIFIED"):
        raise HTTPException(status_code=400, detail="Invalid or expired reset challenge.")

    if challenge.expires_at < utcnow():
        challenge.status = "EXPIRED"
        db.commit()
        raise HTTPException(status_code=400, detail="Code expired. Request a new one.")

    if challenge.attempts >= challenge.max_attempts:
        challenge.status = "LOCKED"
        db.commit()
        raise HTTPException(status_code=400, detail="Too many attempts. Request a new code.")

    code = (otp or "").strip()
    if not re.fullmatch(r"\d{6}", code):
        raise HTTPException(status_code=400, detail="Enter the 6-digit code.")

    challenge.attempts += 1
    if not hmac.compare_digest(challenge.otp_hash, _otp_hmac(code)):
        db.commit()
        remaining = max(0, challenge.max_attempts - challenge.attempts)
        raise HTTPException(
            status_code=400,
            detail=f"Incorrect code. {remaining} attempt{'s' if remaining != 1 else ''} remaining.",
        )

    challenge.status = "VERIFIED"
    challenge.verified_at = utcnow()
    user = db.get(User, challenge.user_id)
    if not user or not user.is_active:
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid or expired reset challenge.")

    reset_token = create_token(
        user.user_id,
        {"challenge_id": challenge.challenge_id},
        timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
        token_type="password_reset",
    )
    write_audit(
        db,
        actor_user_id=user.user_id,
        tenant_id=user.tenant_id,
        entity_type="password_reset",
        entity_id=challenge.challenge_id,
        action="PASSWORD_RESET_OTP_VERIFIED",
    )
    db.commit()
    return {
        "message": "Code verified. Set a new password.",
        "reset_token": reset_token,
        "expires_in_seconds": RESET_TOKEN_TTL_MINUTES * 60,
    }


def reset_password(
    db: Session,
    *,
    reset_token: str,
    new_password: str,
    new_password_confirm: str,
) -> dict:
    if not new_password or len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    if new_password != new_password_confirm:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    try:
        payload = decode_token(reset_token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.") from exc

    if payload.get("type") != "password_reset":
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    challenge_id = payload.get("challenge_id")
    user_id = payload.get("sub")
    challenge = db.get(PasswordResetChallenge, challenge_id) if challenge_id else None
    if not challenge or challenge.user_id != user_id or challenge.status != "VERIFIED":
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")
    if challenge.expires_at < utcnow():
        challenge.status = "EXPIRED"
        db.commit()
        raise HTTPException(status_code=400, detail="Reset session expired. Start again.")

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="User not found.")

    user.password_hash = hash_password(new_password)
    challenge.status = "CONSUMED"
    challenge.consumed_at = utcnow()
    write_audit(
        db,
        actor_user_id=user.user_id,
        tenant_id=user.tenant_id,
        entity_type="password_reset",
        entity_id=challenge.challenge_id,
        action="PASSWORD_RESET_COMPLETED",
    )
    db.commit()
    return {"message": "Password updated. You can sign in with your new password."}


def peek_latest_otp_for_tests(db: Session, challenge_id: str) -> Optional[str]:
    """Test helper: recover OTP from notification body_preview when present."""
    from app.models.notification import NotificationDelivery

    row = (
        db.query(NotificationDelivery)
        .filter(
            NotificationDelivery.entity_type == "password_reset",
            NotificationDelivery.entity_id == challenge_id,
            NotificationDelivery.event_type == "PASSWORD_RESET_OTP",
        )
        .order_by(NotificationDelivery.created_at.desc())
        .first()
    )
    if not row or not row.body_preview:
        return None
    match = re.search(r"\b(\d{6})\b", row.body_preview)
    return match.group(1) if match else None
