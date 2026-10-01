from fastapi import APIRouter, HTTPException
from sqlalchemy import or_

from app.core.deps import DbDep, get_user_permissions
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.models.user import User
from app.schemas.common import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    MessageOut,
    PasswordResetChannelsOut,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from app.services import password_reset as password_reset_service

router = APIRouter(prefix="/auth")


def _token_for(db, user: User) -> TokenResponse:
    perms = get_user_permissions(db, user.user_id)
    claims = {
        "user_type": user.user_type,
        "tenant_id": user.tenant_id,
        "username": user.username,
    }
    return TokenResponse(
        access_token=create_access_token(user.user_id, claims),
        refresh_token=create_refresh_token(user.user_id, claims),
        user_type=user.user_type,
        full_name=user.full_name,
        tenant_id=user.tenant_id,
        permissions=perms,
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: DbDep):
    user = (
        db.query(User)
        .filter(
            or_(
                User.username == body.username,
                User.email == body.username,
                User.phone_number == body.username,
            )
        )
        .first()
    )
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)
        db.commit()
    return _token_for(db, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: DbDep):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = db.get(User, payload.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    return _token_for(db, user)


@router.post("/logout")
def logout():
    return {"message": "Logged out"}


@router.get("/password-reset/channels", response_model=PasswordResetChannelsOut)
def password_reset_channels(db: DbDep):
    """Public: which OTP delivery channels are currently enabled."""
    return PasswordResetChannelsOut(**password_reset_service.available_channels(db))


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(body: ForgotPasswordRequest, db: DbDep):
    result = password_reset_service.request_otp(db, identifier=body.identifier, channel=body.channel)
    return ForgotPasswordResponse(**result)


@router.post("/verify-otp", response_model=VerifyOtpResponse)
def verify_otp(body: VerifyOtpRequest, db: DbDep):
    result = password_reset_service.verify_otp(db, challenge_id=body.challenge_id, otp=body.otp)
    return VerifyOtpResponse(**result)


@router.post("/reset-password", response_model=MessageOut)
def reset_password(body: ResetPasswordRequest, db: DbDep):
    result = password_reset_service.reset_password(
        db,
        reset_token=body.reset_token,
        new_password=body.new_password,
        new_password_confirm=body.new_password_confirm,
    )
    return MessageOut(**result)
