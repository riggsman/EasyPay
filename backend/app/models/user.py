from typing import Optional

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, StatusMixin, new_id


class User(Base, TimestampMixin, StatusMixin):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("usr_"))
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    user_type: Mapped[str] = mapped_column(String(32), default="STAFF")  # STAFF | PAYER | PLATFORM_ADMIN
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tenants.tenant_id"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Role(Base, TimestampMixin, StatusMixin):
    __tablename__ = "roles"

    role_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("rol_"))
    role_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    role_name: Mapped[str] = mapped_column(String(128), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), default="TENANT")  # PLATFORM | TENANT | PAYER
    description: Mapped[Optional[str]] = mapped_column(String(255))


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    permission_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("prm_"))
    permission_code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_perm"),)

    role_permission_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("rp_"))
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.role_id"), nullable=False, index=True)
    permission_id: Mapped[str] = mapped_column(String(36), ForeignKey("permissions.permission_id"), nullable=False)


class UserRole(Base, TimestampMixin):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", "tenant_id", name="uq_user_role_tenant"),)

    user_role_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: new_id("ur_"))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.user_id"), nullable=False, index=True)
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.role_id"), nullable=False, index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tenants.tenant_id"), index=True)
