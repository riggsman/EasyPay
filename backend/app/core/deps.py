from typing import Annotated, List, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import Permission, Role, RolePermission, User, UserRole

security = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(self, user: User, permissions: List[str], claims: dict):
        self.user = user
        self.permissions = permissions
        self.claims = claims

    @property
    def user_id(self) -> str:
        return self.user.user_id

    @property
    def tenant_id(self) -> Optional[str]:
        return self.user.tenant_id or self.claims.get("tenant_id")

    @property
    def user_type(self) -> str:
        return self.user.user_type

    def has_permission(self, code: str) -> bool:
        if self.user.user_type == "PLATFORM_ADMIN":
            return True
        return code in self.permissions or "*" in self.permissions


def get_user_permissions(db: Session, user_id: str) -> List[str]:
    rows = (
        db.query(Permission.permission_code)
        .join(RolePermission, RolePermission.permission_id == Permission.permission_id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .filter(UserRole.user_id == user_id)
        .all()
    )
    return [r[0] for r in rows]


def get_current_user(
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> CurrentUser:
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(creds.credentials)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.get(User, payload.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive or not found")
    perms = get_user_permissions(db, user.user_id)
    return CurrentUser(user, perms, payload)


def require_permissions(*codes: str):
    def _dep(current: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if current.user.user_type == "PLATFORM_ADMIN":
            return current
        if not any(current.has_permission(c) for c in codes):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current

    return _dep


DbDep = Annotated[Session, Depends(get_db)]
UserDep = Annotated[CurrentUser, Depends(get_current_user)]
