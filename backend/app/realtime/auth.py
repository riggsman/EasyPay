from dataclasses import dataclass
from typing import Optional

from app.core.security import decode_token


@dataclass(frozen=True)
class SocketIdentity:
    user_id: str
    user_type: str
    tenant_id: Optional[str]
    username: Optional[str]


def authenticate_socket(access_token: str) -> SocketIdentity:
    payload = decode_token(access_token)
    if payload.get("type") != "access":
        raise ValueError("invalid token type")
    user_id = payload.get("sub")
    if not user_id:
        raise ValueError("missing subject")
    return SocketIdentity(
        user_id=user_id,
        user_type=payload.get("user_type") or "UNKNOWN",
        tenant_id=payload.get("tenant_id"),
        username=payload.get("username"),
    )
