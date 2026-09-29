from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr

from app.core.deps import DbDep, UserDep, require_permissions
from app.core.security import hash_password
from app.models.user import Role, User, UserRole

router = APIRouter(prefix="/users")


class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    full_name: Optional[str] = None
    user_type: str = "STAFF"
    tenant_id: Optional[str] = None
    role_code: Optional[str] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    user_type: str
    tenant_id: Optional[str] = None
    is_active: bool


@router.get("/me", response_model=UserOut)
def me(current: UserDep):
    return current.user


@router.post("", response_model=UserOut)
def create_user(body: UserCreate, db: DbDep, current = Depends(require_permissions("users:write"))):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=422, detail="Username taken")
    user = User(
        username=body.username,
        email=str(body.email) if body.email else None,
        phone_number=body.phone_number,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        user_type=body.user_type,
        tenant_id=body.tenant_id,
    )
    db.add(user)
    db.flush()
    if body.role_code:
        role = db.query(Role).filter(Role.role_code == body.role_code).first()
        if role:
            db.add(UserRole(user_id=user.user_id, role_id=role.role_id, tenant_id=body.tenant_id))
    db.commit()
    db.refresh(user)
    return user
