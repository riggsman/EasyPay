from typing import List

from fastapi import APIRouter, HTTPException
from sqlalchemy import or_

from app.core.deps import DbDep
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.core.deps import get_user_permissions
from app.models.user import User
from app.schemas.common import LoginRequest, RefreshRequest, TokenResponse

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
