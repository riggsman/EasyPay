from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from passlib.context import CryptContext

from app.core.config import get_settings

_argon2 = PasswordHasher()
_bcrypt_legacy = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _argon2.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    if hashed.startswith("$argon2"):
        try:
            return _argon2.verify(hashed, plain)
        except (VerifyMismatchError, InvalidHashError):
            return False
    # Legacy bcrypt hashes from earlier seeds
    try:
        return _bcrypt_legacy.verify(plain, hashed)
    except Exception:
        return False


def needs_rehash(hashed: str) -> bool:
    if not hashed.startswith("$argon2"):
        return True
    try:
        return _argon2.check_needs_rehash(hashed)
    except Exception:
        return True


def create_token(subject: str, claims: dict[str, Any], expires_delta: timedelta, token_type: str = "access") -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        **claims,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(subject: str, claims: Optional[dict[str, Any]] = None) -> str:
    settings = get_settings()
    return create_token(
        subject,
        claims or {},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "access",
    )


def create_refresh_token(subject: str, claims: Optional[dict[str, Any]] = None) -> str:
    settings = get_settings()
    return create_token(
        subject,
        claims or {},
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "refresh",
    )


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
