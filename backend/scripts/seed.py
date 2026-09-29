"""Seed Cameroon / Southwest / Kumba councils + platform admin + sample data."""
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password
from app.db.models import Base
from app.db.session import SessionLocal, engine
from app.db.base import utcnow
from app.models.platform import Platform
from app.models.geography import GeographicUnit, TenantGeographicUnit
from app.models.tenant import Tenant
from app.models.user import User, Role, Permission, RolePermission, UserRole
from app.models.revenue import RevenueType, PaymentChannel, FeeConfiguration, CommissionAgreement
from app.models.obligation import Obligation
from app.models.payer import Payer, PayerGeographicHistory


PERMISSIONS = [
    "platforms:read",
    "platforms:write",
    "geography:write",
    "tenants:read",
    "tenants:write",
    "users:write",
    "revenue:write",
    "obligations:write",
    "zone_changes:review",
    "receipts:revoke",
    "settlements:read",
    "settlements:write",
    "settlements:approve",
    "dashboards:read",
    "dashboards:platform",
    "reports:read",
    "providers:write",
    "system:configure",
]

# Default SUPER ADMIN (login via username, email, or phone)
DEFAULT_SUPER_ADMIN = {
    "username": "admin",
    "email": "wireitapp@gmail.com",
    "phone_number": "682835503",
    "password": "admin123",
    "full_name": "Super Admin",
}


def ensure_super_admin_role(db) -> Role:
    """Ensure SUPER_ADMIN role exists with full permission set."""
    role = db.query(Role).filter(Role.role_code == "SUPER_ADMIN").first()
    if not role:
        role = Role(
            role_code="SUPER_ADMIN",
            role_name="Super Administrator",
            scope="PLATFORM",
        )
        db.add(role)
        db.flush()

    for code in PERMISSIONS:
        perm = db.query(Permission).filter(Permission.permission_code == code).first()
        if not perm:
            perm = Permission(permission_code=code, description=code)
            db.add(perm)
            db.flush()
        link = (
            db.query(RolePermission)
            .filter(
                RolePermission.role_id == role.role_id,
                RolePermission.permission_id == perm.permission_id,
            )
            .first()
        )
        if not link:
            db.add(RolePermission(role_id=role.role_id, permission_id=perm.permission_id))
    return role


def ensure_default_super_admin(db) -> User:
    """Create or update the default SUPER_ADMIN seed user."""
    role = ensure_super_admin_role(db)

    user = (
        db.query(User)
        .filter(
            (User.username == DEFAULT_SUPER_ADMIN["username"])
            | (User.email == DEFAULT_SUPER_ADMIN["email"])
            | (User.phone_number == DEFAULT_SUPER_ADMIN["phone_number"])
        )
        .first()
    )
    if user:
        user.username = DEFAULT_SUPER_ADMIN["username"]
        user.email = DEFAULT_SUPER_ADMIN["email"]
        user.phone_number = DEFAULT_SUPER_ADMIN["phone_number"]
        user.full_name = DEFAULT_SUPER_ADMIN["full_name"]
        user.user_type = "SUPER_ADMIN"
        user.is_active = True
        user.password_hash = hash_password(DEFAULT_SUPER_ADMIN["password"])
    else:
        user = User(
            username=DEFAULT_SUPER_ADMIN["username"],
            email=DEFAULT_SUPER_ADMIN["email"],
            phone_number=DEFAULT_SUPER_ADMIN["phone_number"],
            password_hash=hash_password(DEFAULT_SUPER_ADMIN["password"]),
            full_name=DEFAULT_SUPER_ADMIN["full_name"],
            user_type="SUPER_ADMIN",
        )
        db.add(user)
        db.flush()

    link = (
        db.query(UserRole)
        .filter(UserRole.user_id == user.user_id, UserRole.role_id == role.role_id)
        .first()
    )
    if not link:
        db.add(UserRole(user_id=user.user_id, role_id=role.role_id))
    return user


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Platform).first():
            admin = ensure_default_super_admin(db)
            db.commit()
            print("Already seeded — ensured default SUPER ADMIN")
            print(
                f"  {admin.username} / {DEFAULT_SUPER_ADMIN['password']} "
                f"({admin.email}, {admin.phone_number})"
            )
            return

        platform = Platform(
            platform_code="EASYPAY",
            platform_name="EasyPay",
            legal_name="EasyPay Collection Platform",
            email=DEFAULT_SUPER_ADMIN["email"],
            default_currency="XAF",
        )
        db.add(platform)
        db.flush()

        # Geography tree
        cm = GeographicUnit(unit_code="CM", unit_name="Cameroon", unit_type="COUNTRY", country_code="CM")
        db.add(cm)
        db.flush()
        sw = GeographicUnit(parent_id=cm.geographic_unit_id, unit_code="CM-SW", unit_name="Southwest", unit_type="REGION", country_code="CM")
        db.add(sw)
        db.flush()
        meme = GeographicUnit(parent_id=sw.geographic_unit_id, unit_code="CM-SW-MEME", unit_name="Meme", unit_type="DIVISION", country_code="CM")
        db.add(meme)
        db.flush()
        kumba = GeographicUnit(parent_id=meme.geographic_unit_id, unit_code="CM-SW-MEME-KUMBA", unit_name="Kumba", unit_type="TOWN", country_code="CM")
        db.add(kumba)
        db.flush()

        councils = []
        for code, name in [("KUMBA-01", "Kumba 1"), ("KUMBA-02", "Kumba 2"), ("KUMBA-03", "Kumba 3")]:
            g = GeographicUnit(
                parent_id=kumba.geographic_unit_id,
                unit_code=code,
                unit_name=name,
                unit_type="COUNCIL",
                country_code="CM",
            )
            db.add(g)
            db.flush()
            councils.append(g)

        tenants = []
        for g, tcode, tname in [
            (councils[0], "KUMBA1", "Kumba 1 Council"),
            (councils[1], "KUMBA2", "Kumba 2 Council"),
            (councils[2], "KUMBA3", "Kumba 3 Council"),
        ]:
            t = Tenant(
                tenant_code=tcode,
                organization_name=tname,
                organization_type="COUNCIL",
                currency="XAF",
                email=f"{tcode.lower()}@council.local",
                zone_change_mode="IMMEDIATE",
                verification="VERIFIED",
                status="ACTIVE",
            )
            db.add(t)
            db.flush()
            db.add(
                TenantGeographicUnit(
                    tenant_id=t.tenant_id,
                    geographic_unit_id=g.geographic_unit_id,
                    relationship_type="PRIMARY_COUNCIL",
                    is_primary=True,
                    effective_from=utcnow(),
                )
            )
            tenants.append((t, g))

        # Permissions & roles
        perm_map = {}
        for code in PERMISSIONS:
            p = Permission(permission_code=code, description=code)
            db.add(p)
            db.flush()
            perm_map[code] = p

        roles = {
            "SUPER_ADMIN": ("Super Administrator", "PLATFORM", list(PERMISSIONS)),
            "PLATFORM_ADMIN": ("Platform Administrator", "PLATFORM", list(PERMISSIONS)),
            "TENANT_ADMIN": (
                "Council Administrator",
                "TENANT",
                [
                    "tenants:read",
                    "revenue:write",
                    "obligations:write",
                    "zone_changes:review",
                    "settlements:read",
                    "settlements:write",
                    "settlements:approve",
                    "dashboards:read",
                    "reports:read",
                ],
            ),
            "PAYER": ("Payer", "PAYER", []),
        }
        role_objs = {}
        for code, (name, scope, perms) in roles.items():
            r = Role(role_code=code, role_name=name, scope=scope)
            db.add(r)
            db.flush()
            role_objs[code] = r
            for pc in perms:
                db.add(RolePermission(role_id=r.role_id, permission_id=perm_map[pc].permission_id))

        admin = ensure_default_super_admin(db)
        db.flush()

        from app.services.providers import store as provider_store

        provider_store.upsert_provider_config(
            db,
            provider_code=provider_store.PROVIDER_CAMPAY,
            display_name="Campay",
            enabled=True,
            secrets={
                "username": "demo",
                "password": "demo",
                "base_url": "https://demo.campay.net/api",
                "mock": True,
                "bank_transfer_path": "/withdraw/",
            },
            public_meta={"environment": "sandbox", "mock": True},
            updated_by=admin.user_id,
        )

        # Tenant admins
        for t, g in tenants:
            u = User(
                username=f"{t.tenant_code.lower()}_admin",
                email=t.email,
                password_hash=hash_password("council123"),
                full_name=f"{t.organization_name} Admin",
                user_type="STAFF",
                tenant_id=t.tenant_id,
            )
            db.add(u)
            db.flush()
            db.add(UserRole(user_id=u.user_id, role_id=role_objs["TENANT_ADMIN"].role_id, tenant_id=t.tenant_id))

        # Payment channels
        for code, name in [
            ("MOBILE_MONEY", "Mobile Money"),
            ("BANK", "Bank Transfer"),
            ("CARD", "Card"),
            ("OTHER", "Other"),
        ]:
            db.add(PaymentChannel(code=code, name=name))

        # Revenue types + fees for each council
        revenue_defs = [
            ("BIZ_LICENSE", "Business License", Decimal("50000")),
            ("WASTE_LEVY", "Waste Levy", Decimal("5000")),
            ("MARKET_LEVY", "Market Levy", Decimal("5000")),
            ("SIGNBOARD", "Signboard Fee", Decimal("10000")),
        ]
        for t, g in tenants:
            for code, name, amt in revenue_defs:
                rt = RevenueType(
                    tenant_id=t.tenant_id,
                    geographic_unit_id=g.geographic_unit_id,
                    code=code,
                    name=name,
                    default_amount=amt,
                    currency="XAF",
                )
                db.add(rt)
                db.flush()
                db.add(
                    FeeConfiguration(
                        tenant_id=t.tenant_id,
                        geographic_unit_id=g.geographic_unit_id,
                        revenue_type_id=rt.revenue_type_id,
                        fee_type="FLAT",
                        fee_value=Decimal("500"),
                    )
                )
                db.add(
                    CommissionAgreement(
                        tenant_id=t.tenant_id,
                        revenue_type_id=rt.revenue_type_id,
                        commission_type="PERCENT",
                        commission_value=Decimal("5"),
                    )
                )

        # Sample payer in Kumba 1
        t1, g1 = tenants[0]
        payer_user = User(
            username="abctrading",
            email="abc@traders.local",
            phone_number="670000001",
            password_hash=hash_password("payer123"),
            full_name="ABC Trading",
            user_type="PAYER",
            tenant_id=t1.tenant_id,
        )
        db.add(payer_user)
        db.flush()
        db.add(UserRole(user_id=payer_user.user_id, role_id=role_objs["PAYER"].role_id, tenant_id=t1.tenant_id))
        payer = Payer(
            user_id=payer_user.user_id,
            tenant_id=t1.tenant_id,
            payer_reference="PYR-2026-000001",
            payer_type="BUSINESS",
            full_name="ABC Trading Owner",
            business_name="ABC Trading",
            email="abc@traders.local",
            phone_number="670000001",
            address="Kumba Main Market",
            current_geographic_unit_id=g1.geographic_unit_id,
        )
        db.add(payer)
        db.flush()
        db.add(
            PayerGeographicHistory(
                payer_id=payer.payer_id,
                geographic_unit_id=g1.geographic_unit_id,
                tenant_id=t1.tenant_id,
                effective_from=datetime(2026, 1, 1),
                change_reason="Initial registration",
                change_source="SEED",
                changed_by=admin.user_id,
            )
        )

        biz = (
            db.query(RevenueType)
            .filter(RevenueType.tenant_id == t1.tenant_id, RevenueType.code == "BIZ_LICENSE")
            .first()
        )
        waste = (
            db.query(RevenueType)
            .filter(RevenueType.tenant_id == t1.tenant_id, RevenueType.code == "WASTE_LEVY")
            .first()
        )
        db.add(
            Obligation(
                payer_id=payer.payer_id,
                tenant_id=t1.tenant_id,
                geographic_unit_id=g1.geographic_unit_id,
                revenue_type_id=biz.revenue_type_id,
                description="Business License — 2026",
                amount=Decimal("50000"),
                balance=Decimal("50000"),
                status="DUE",
            )
        )
        db.add(
            Obligation(
                payer_id=payer.payer_id,
                tenant_id=t1.tenant_id,
                geographic_unit_id=g1.geographic_unit_id,
                revenue_type_id=waste.revenue_type_id,
                description="Waste Levy — Sep 2026",
                amount=Decimal("5000"),
                balance=Decimal("5000"),
                status="DUE",
            )
        )

        db.commit()
        print("Seed complete.")
        print(
            f"  {DEFAULT_SUPER_ADMIN['username']} / {DEFAULT_SUPER_ADMIN['password']} "
            f"(SUPER ADMIN · {DEFAULT_SUPER_ADMIN['email']} · {DEFAULT_SUPER_ADMIN['phone_number']})"
        )
        print("  kumba1_admin / council123 (tenant)")
        print("  abctrading / payer123 (payer in Kumba 1)")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
