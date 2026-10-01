"""Seed EasyPay foundation + sample demo data currently used in the product.

Creates:
  - Platform, Cameroon/Southwest/Kumba geography, 3 council tenants
    (full national regions/divisions/councils: scripts/populate_cameroon_geography.py)
  - SUPER ADMIN (wireitapp@gmail.com / 682835503), council admins, demo payers
  - Revenue types, fees, commissions, payment channels
  - Campay / Email / WhatsApp / SMS provider configs (Campay mock)
  - Notification channel toggles
  - Sample obligations + settled Mobile Money payments (via payment service)
  - Failed-transaction demos (payer debit fail, council credit retry, manual intervention)

Safe to re-run: foundation is skipped when present; sample users/providers/payments
and failure demos are ensured idempotently (failure demos are fully reset each run).
"""
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password
from app.db.models import Base
from app.db.session import SessionLocal, engine
from app.db.base import new_id, utcnow
from app.models.platform import Platform
from app.models.geography import GeographicUnit, TenantGeographicUnit
from app.models.tenant import Tenant
from app.models.user import User, Role, Permission, RolePermission, UserRole
from app.models.revenue import RevenueType, PaymentChannel, FeeConfiguration, CommissionAgreement
from app.models.obligation import Obligation
from app.models.payer import Payer, PayerGeographicHistory
from app.models.transaction import Transaction, TransactionEvent
from app.schemas.common import PaymentInitiateRequest
from app.services.notifications.config import (
    CONFIG_EMAIL,
    CONFIG_SMS,
    CONFIG_WHATSAPP,
    upsert_channel_toggle,
)
from app.services.payments import complete_payment_happy_path, initiate_payment
from app.services.providers import store as provider_store


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

DEFAULT_SUPER_ADMIN = {
    "username": "admin",
    "email": "wireitapp@gmail.com",
    "phone_number": "682835503",
    "password": "admin123",
    "full_name": "Super Admin",
}

REVENUE_DEFS = [
    ("BIZ_LICENSE", "Business License", Decimal("50000")),
    ("WASTE_LEVY", "Waste Levy", Decimal("5000")),
    ("MARKET_LEVY", "Market Levy", Decimal("5000")),
    ("SIGNBOARD", "Signboard Fee", Decimal("10000")),
]

# Curated sample payers matching the demo data used in the running system.
SAMPLE_PAYERS = [
    {
        "username": "abctrading",
        "password": "payer123",
        "email": "abc@traders.local",
        "phone_number": "670000001",
        "full_name": "ABC Trading",
        "owner_name": "ABC Trading Owner",
        "business_name": "ABC Trading",
        "address": "Kumba Main Market",
        "tenant_code": "KUMBA1",
        "payer_reference": "PYR-2026-000001",
        "obligations": [
            {
                "revenue_code": "BIZ_LICENSE",
                "description": "Business License — 2026",
                "amount": Decimal("50000"),
                "settle": False,
            },
            {
                "revenue_code": "WASTE_LEVY",
                "description": "Waste Levy — Sep 2026",
                "amount": Decimal("5000"),
                "settle": True,
                "idempotency_key": "seed-abc-waste-levy-2026-09",
            },
        ],
    },
    {
        "username": "mambagroceries",
        "password": "payer123",
        "email": "mamba@traders.local",
        "phone_number": "670000002",
        "full_name": "Mamba Groceries",
        "owner_name": "Mamba Groceries Owner",
        "business_name": "Mamba Groceries",
        "address": "Fiango Market",
        "tenant_code": "KUMBA1",
        "payer_reference": "PYR-SEED-000002",
        "obligations": [
            {
                "revenue_code": "MARKET_LEVY",
                "description": "Market Levy — Sep 2026",
                "amount": Decimal("5000"),
                "settle": True,
                "idempotency_key": "seed-mamba-market-2026-09",
            },
            {
                "revenue_code": "SIGNBOARD",
                "description": "Signboard Fee — 2026",
                "amount": Decimal("10000"),
                "settle": True,
                "idempotency_key": "seed-mamba-signboard-2026",
            },
        ],
    },
    {
        "username": "buearoasters",
        "password": "payer123",
        "email": "buea@traders.local",
        "phone_number": "670000003",
        "full_name": "Buea Roasters",
        "owner_name": "Buea Roasters Owner",
        "business_name": "Buea Roasters",
        "address": "Kumba 2 Commercial Ave",
        "tenant_code": "KUMBA2",
        "payer_reference": "PYR-SEED-000003",
        "obligations": [
            {
                "revenue_code": "BIZ_LICENSE",
                "description": "Business License — 2026",
                "amount": Decimal("50000"),
                "settle": True,
                "idempotency_key": "seed-buea-biz-2026",
            },
            {
                "revenue_code": "WASTE_LEVY",
                "description": "Waste Levy — Sep 2026",
                "amount": Decimal("5000"),
                "settle": True,
                "idempotency_key": "seed-buea-waste-2026-09",
            },
        ],
    },
    {
        "username": "threeconner",
        "password": "payer123",
        "email": "three@traders.local",
        "phone_number": "670000004",
        "full_name": "Three Corner Shop",
        "owner_name": "Three Corner Owner",
        "business_name": "Three Corner Shop",
        "address": "Kumba 3 Junction",
        "tenant_code": "KUMBA3",
        "payer_reference": "PYR-SEED-000004",
        "obligations": [
            {
                "revenue_code": "MARKET_LEVY",
                "description": "Market Levy — Sep 2026",
                "amount": Decimal("5000"),
                "settle": True,
                "idempotency_key": "seed-threecorner-market-2026-09",
            },
        ],
    },
]


def ensure_super_admin_role(db) -> Role:
    role = db.query(Role).filter(Role.role_code == "SUPER_ADMIN").first()
    if not role:
        role = Role(role_code="SUPER_ADMIN", role_name="Super Administrator", scope="PLATFORM")
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


def ensure_providers(db, admin: User) -> None:
    """Seed encrypted provider configs used by the running demo."""
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
    provider_store.upsert_provider_config(
        db,
        provider_code=provider_store.PROVIDER_EMAIL,
        display_name="Email SMTP",
        enabled=True,
        secrets={
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_user": "ops@easypay.local",
            "smtp_password": "demo-mail-secret",
            "from_email": "noreply@easypay.local",
            "mock": True,
        },
        public_meta={"mock": True},
        updated_by=admin.user_id,
    )
    provider_store.upsert_provider_config(
        db,
        provider_code=provider_store.PROVIDER_WHATSAPP,
        display_name="WhatsApp",
        enabled=True,
        secrets={
            "api_url": "https://graph.facebook.com/v17.0",
            "access_token": "demo-wa-token",
            "phone_number_id": "000000000000000",
            "mock": True,
        },
        public_meta={"mock": True},
        updated_by=admin.user_id,
    )
    provider_store.upsert_provider_config(
        db,
        provider_code=provider_store.PROVIDER_SMS,
        display_name="SMS",
        enabled=True,
        secrets={
            "api_url": "https://sms.example.com/send",
            "api_key": "demo-sms-key",
            "sender_id": "EASYPAY",
            "mock": True,
        },
        public_meta={"mock": True},
        updated_by=admin.user_id,
    )


def ensure_notification_toggles(db) -> None:
    """Match current platform notification defaults (email on, SMS off, WhatsApp on)."""
    upsert_channel_toggle(db, None, CONFIG_EMAIL, True, "Platform email notifications")
    upsert_channel_toggle(db, None, CONFIG_SMS, False, "Platform SMS notifications (toggleable)")
    upsert_channel_toggle(db, None, CONFIG_WHATSAPP, True, "Platform WhatsApp notifications")
    db.commit()


def _tenant_by_code(db, code: str) -> Tenant:
    t = db.query(Tenant).filter(Tenant.tenant_code == code).first()
    if not t:
        raise RuntimeError(f"Tenant {code} missing — run full seed first")
    return t


def _primary_geo(db, tenant_id: str) -> GeographicUnit:
    link = (
        db.query(TenantGeographicUnit)
        .filter(TenantGeographicUnit.tenant_id == tenant_id, TenantGeographicUnit.is_primary.is_(True))
        .first()
    )
    if not link:
        raise RuntimeError(f"Primary geography missing for tenant {tenant_id}")
    return db.get(GeographicUnit, link.geographic_unit_id)


def _revenue(db, tenant_id: str, code: str) -> RevenueType:
    rt = (
        db.query(RevenueType)
        .filter(RevenueType.tenant_id == tenant_id, RevenueType.code == code)
        .first()
    )
    if not rt:
        raise RuntimeError(f"Revenue type {code} missing for tenant {tenant_id}")
    return rt


def ensure_sample_payer(db, admin: User, role_payer: Role, spec: dict) -> Payer:
    tenant = _tenant_by_code(db, spec["tenant_code"])
    geo = _primary_geo(db, tenant.tenant_id)

    user = db.query(User).filter(User.username == spec["username"]).first()
    if not user:
        user = User(
            username=spec["username"],
            email=spec["email"],
            phone_number=spec["phone_number"],
            password_hash=hash_password(spec["password"]),
            full_name=spec["full_name"],
            user_type="PAYER",
            tenant_id=tenant.tenant_id,
        )
        db.add(user)
        db.flush()
    else:
        user.email = spec["email"]
        user.phone_number = spec["phone_number"]
        user.full_name = spec["full_name"]
        user.user_type = "PAYER"
        user.tenant_id = tenant.tenant_id
        user.password_hash = hash_password(spec["password"])
        user.is_active = True

    if not db.query(UserRole).filter(UserRole.user_id == user.user_id, UserRole.role_id == role_payer.role_id).first():
        db.add(UserRole(user_id=user.user_id, role_id=role_payer.role_id, tenant_id=tenant.tenant_id))

    payer = db.query(Payer).filter(Payer.user_id == user.user_id).first()
    if not payer:
        payer = db.query(Payer).filter(Payer.payer_reference == spec["payer_reference"]).first()
    if not payer:
        payer = Payer(
            user_id=user.user_id,
            tenant_id=tenant.tenant_id,
            payer_reference=spec["payer_reference"],
            payer_type="BUSINESS",
            full_name=spec["owner_name"],
            business_name=spec["business_name"],
            email=spec["email"],
            phone_number=spec["phone_number"],
            address=spec["address"],
            current_geographic_unit_id=geo.geographic_unit_id,
        )
        db.add(payer)
        db.flush()
        db.add(
            PayerGeographicHistory(
                payer_id=payer.payer_id,
                geographic_unit_id=geo.geographic_unit_id,
                tenant_id=tenant.tenant_id,
                effective_from=datetime(2026, 1, 1),
                change_reason="Initial registration",
                change_source="SEED",
                changed_by=admin.user_id,
            )
        )
    else:
        payer.user_id = user.user_id
        payer.tenant_id = tenant.tenant_id
        payer.payer_reference = spec["payer_reference"]
        payer.full_name = spec["owner_name"]
        payer.business_name = spec["business_name"]
        payer.email = spec["email"]
        payer.phone_number = spec["phone_number"]
        payer.address = spec["address"]
        payer.current_geographic_unit_id = geo.geographic_unit_id

    db.flush()
    return payer


def ensure_obligation(db, payer: Payer, spec: dict) -> Obligation:
    revenue = _revenue(db, payer.tenant_id, spec["revenue_code"])
    obl = (
        db.query(Obligation)
        .filter(
            Obligation.payer_id == payer.payer_id,
            Obligation.revenue_type_id == revenue.revenue_type_id,
            Obligation.description == spec["description"],
        )
        .first()
    )
    if not obl:
        obl = Obligation(
            payer_id=payer.payer_id,
            tenant_id=payer.tenant_id,
            geographic_unit_id=payer.current_geographic_unit_id,
            revenue_type_id=revenue.revenue_type_id,
            description=spec["description"],
            amount=spec["amount"],
            balance=spec["amount"],
            status="DUE",
        )
        db.add(obl)
        db.flush()
    return obl


def settle_obligation_if_needed(db, payer: Payer, obl: Obligation, idempotency_key: str, actor_user_id: str) -> Transaction | None:
    if obl.status == "PAID" or obl.balance <= 0:
        return (
            db.query(Transaction)
            .filter(Transaction.obligation_id == obl.obligation_id, Transaction.status == "SETTLED")
            .first()
        )

    existing = (
        db.query(Transaction)
        .filter(Transaction.idempotency_key == idempotency_key)
        .first()
    )
    if existing:
        if existing.status != "SETTLED":
            return complete_payment_happy_path(db, existing.transaction_id, actor_user_id)
        return existing

    txn = initiate_payment(
        db,
        payer,
        PaymentInitiateRequest(
            obligation_id=obl.obligation_id,
            payment_channel="MOBILE_MONEY",
            idempotency_key=idempotency_key,
            phone_number=payer.phone_number,
        ),
        actor_user_id,
    )
    if txn.status != "SETTLED":
        txn = complete_payment_happy_path(db, txn.transaction_id, actor_user_id)
    return txn


def ensure_tenant_payout_destinations(db) -> None:
    for t in db.query(Tenant).all():
        suffix = (t.tenant_code or "1")[-1]
        if not t.momo_number:
            t.momo_number = f"67010000{suffix}"
        if not t.bank_account_number:
            t.bank_account_number = f"10001{suffix}9988"
        if not t.phone_number:
            t.phone_number = f"2337{suffix}00001"
    db.flush()


# Curated failed-payment demos (ABC Trading / Kumba 1). Amounts are distinct for easy spotting.
FAILURE_DEMO_SPECS = [
    {
        "ref": "TXN-DEMO-DEBIT-FAIL",
        "status": "FAILED",
        "failure_stage": "DEBIT",
        "failure_reason": (
            "Payer debit failed: MoMo wallet declined collection (insufficient funds)"
        ),
        "amount": Decimal("12500"),
        "service_fee": Decimal("500"),
        "commission_amount": Decimal("625"),
        "revenue_code": "MARKET_LEVY",
        "obligation_description": "Market Levy — debit failure demo (do not settle)",
        "provider_status": "FAILED",
        "credit_retry_count": 0,
        "hours_ago": 6,
    },
    {
        "ref": "TXN-DEMO-CREDIT-FAIL",
        "status": "FAILED",
        "failure_stage": "CREDIT",
        "failure_reason": (
            "Council credit failed: payout provider returned insufficient float "
            "for destination account (simulated)"
        ),
        "amount": Decimal("18000"),
        "service_fee": Decimal("500"),
        "commission_amount": Decimal("900"),
        "revenue_code": "SIGNBOARD",
        "obligation_description": "Signboard Fee — credit failure demo (retryable)",
        "provider_status": "SUCCESSFUL",
        "credit_retry_count": 1,
        "hours_ago": 4,
    },
    {
        "ref": "TXN-DEMO-CREDIT-MANUAL",
        "status": "MANUAL_INTERVENTION",
        "failure_stage": "CREDIT",
        "failure_reason": (
            "Council credit failed after retries: destination rejected by payout provider "
            "(simulated unavailable float / invalid MoMo account)"
        ),
        "amount": Decimal("22000"),
        "service_fee": Decimal("500"),
        "commission_amount": Decimal("1100"),
        "revenue_code": "BIZ_LICENSE",
        "obligation_description": "Business License installment — manual intervention demo",
        "provider_status": "SUCCESSFUL",
        "credit_retry_count": None,  # filled with DEFAULT_CREDIT_MAX_RETRIES
        "hours_ago": 2,
    },
]


def ensure_failure_demo_cases(db, admin: User) -> dict:
    """Idempotently seed (and reset) payer-debit / council-credit failure demos.

    Scenarios:
      - TXN-DEMO-DEBIT-FAIL — FAILED immediately after debiting stage (failure_stage=DEBIT)
      - TXN-DEMO-CREDIT-FAIL — FAILED after debit; council credit retryable (failure_stage=CREDIT)
      - TXN-DEMO-CREDIT-MANUAL — MANUAL_INTERVENTION after credit retries exhausted
    """
    from app.services.payments import (
        DEFAULT_CREDIT_MAX_RETRIES,
        ensure_credit_retry_settings,
    )

    ensure_credit_retry_settings(db)
    ensure_tenant_payout_destinations(db)

    payer_user = db.query(User).filter(User.username == "abctrading").first()
    payer = db.query(Payer).filter(Payer.user_id == payer_user.user_id).first() if payer_user else None
    if not payer:
        payer = (
            db.query(Payer)
            .filter(Payer.payer_reference.in_(["PYR-2026-000001", "PYR-SEED-000001"]))
            .first()
        )
    if not payer:
        payer = db.query(Payer).order_by(Payer.created_at.asc()).first()
    if not payer:
        return {"debit_fail": None, "credit_fail": None, "manual": None}

    tenant = db.get(Tenant, payer.tenant_id)
    momo_dest = (tenant.momo_number if tenant else None) or "670100001"
    now = utcnow()
    out: dict[str, str | None] = {"debit_fail": None, "credit_fail": None, "manual": None}

    for spec in FAILURE_DEMO_SPECS:
        revenue = _revenue(db, payer.tenant_id, spec["revenue_code"])
        obl = ensure_obligation(
            db,
            payer,
            {
                "revenue_code": spec["revenue_code"],
                "description": spec["obligation_description"],
                "amount": spec["amount"],
            },
        )
        # Keep demo obligations unpaid so they remain visible as open work
        obl.status = "DUE"
        obl.balance = spec["amount"]

        amount = spec["amount"]
        fee = spec["service_fee"]
        commission = spec["commission_amount"]
        total = amount + fee
        retries = spec["credit_retry_count"]
        if retries is None:
            retries = DEFAULT_CREDIT_MAX_RETRIES
        initiated = now - timedelta(hours=spec["hours_ago"])

        txn = db.query(Transaction).filter(Transaction.transaction_reference == spec["ref"]).first()
        if not txn:
            txn = Transaction(
                transaction_reference=spec["ref"],
                correlation_id=new_id("cor_"),
                idempotency_key=f"seed-{spec['ref'].lower()}",
                payer_id=payer.payer_id,
                transaction_tenant_id=payer.tenant_id,
                transaction_geographic_unit_id=payer.current_geographic_unit_id,
                obligation_id=obl.obligation_id,
                revenue_type_id=revenue.revenue_type_id,
                amount=amount,
                service_fee=fee,
                commission_amount=commission,
                total_amount=total,
                currency="XAF",
                payment_channel="MOBILE_MONEY",
                payment_provider="CAMPAY",
                status=spec["status"],
                initiated_at=initiated,
            )
            db.add(txn)
            db.flush()
        else:
            txn.payer_id = payer.payer_id
            txn.transaction_tenant_id = payer.tenant_id
            txn.transaction_geographic_unit_id = payer.current_geographic_unit_id
            txn.obligation_id = obl.obligation_id
            txn.revenue_type_id = revenue.revenue_type_id
            txn.amount = amount
            txn.service_fee = fee
            txn.commission_amount = commission
            txn.total_amount = total
            txn.currency = "XAF"
            txn.payment_channel = "MOBILE_MONEY"
            txn.payment_provider = "CAMPAY"
            txn.initiated_at = initiated

        # Always restore canonical failure state (tests may settle / escalate demos)
        txn.status = spec["status"]
        txn.failure_stage = spec["failure_stage"]
        txn.failure_reason = spec["failure_reason"]
        txn.credit_retry_count = retries
        txn.payer_msisdn = payer.phone_number
        txn.provider_status = spec["provider_status"]
        txn.provider_reference = f"CAMPAY-DEMO-{spec['ref']}"
        txn.settled_at = None
        txn.collection_id = None
        txn.credit_provider_reference = None
        if spec["failure_stage"] == "CREDIT":
            txn.credit_destination = momo_dest
            txn.credit_payout_method = "MOMO"
        else:
            txn.credit_destination = None
            txn.credit_payout_method = None
        if spec["status"] == "MANUAL_INTERVENTION":
            txn.manual_intervention_at = initiated + timedelta(minutes=45)
            txn.manual_intervention_by = admin.user_id
        else:
            txn.manual_intervention_at = None
            txn.manual_intervention_by = None

        # Rebuild a clean timeline so polluted retry/settle events from UAT do not linger
        db.query(TransactionEvent).filter(TransactionEvent.transaction_id == txn.transaction_id).delete(
            synchronize_session=False
        )
        db.flush()

        # Stagger created_at so timeline order is stable (same-second inserts are unordered)
        timeline: list[tuple[str | None, str, str, int]] = [
            (None, "INITIATED", "Payment initiated", 0),
            ("INITIATED", "PROCESSING", "Payment processing", 1),
        ]
        if spec["failure_stage"] == "DEBIT":
            timeline.append(("PROCESSING", "FAILED", spec["failure_reason"], 2))
        else:
            timeline.append(("PROCESSING", "DEBITED", "Customer account debited via Campay", 2))
            timeline.append(("DEBITED", "FAILED", spec["failure_reason"], 3))
            if spec["status"] == "MANUAL_INTERVENTION":
                timeline.append(
                    (
                        "FAILED",
                        "MANUAL_INTERVENTION",
                        f"Credit retries exhausted ({retries}/{DEFAULT_CREDIT_MAX_RETRIES})",
                        4,
                    )
                )
        for from_status, to_status, note, offset_min in timeline:
            ev = TransactionEvent(
                transaction_id=txn.transaction_id,
                from_status=from_status,
                to_status=to_status,
                note=note,
                actor_user_id=admin.user_id,
            )
            ev.created_at = initiated + timedelta(minutes=offset_min)
            ev.updated_at = ev.created_at
            db.add(ev)
        db.flush()

        if spec["ref"] == "TXN-DEMO-DEBIT-FAIL":
            out["debit_fail"] = txn.transaction_reference
        elif spec["ref"] == "TXN-DEMO-CREDIT-FAIL":
            out["credit_fail"] = txn.transaction_reference
        elif spec["ref"] == "TXN-DEMO-CREDIT-MANUAL":
            out["manual"] = txn.transaction_reference

    return out


def ensure_sample_demo_data(db) -> dict:
    """Ensure curated sample payers, obligations, and settled payments."""
    admin = ensure_default_super_admin(db)
    role_payer = db.query(Role).filter(Role.role_code == "PAYER").first()
    if not role_payer:
        raise RuntimeError("PAYER role missing — run full seed first")

    ensure_providers(db, admin)
    ensure_notification_toggles(db)
    from app.services.history_exports import ensure_default_history_export_settings
    from app.services.branding import ensure_default_platform_logo

    ensure_default_history_export_settings(db)
    ensure_tenant_payout_destinations(db)
    ensure_default_platform_logo(db)
    from app.services.utilities import ensure_sample_utility_services
    from app.services.payment_products import ensure_default_payment_products

    utilities = ensure_sample_utility_services(db)
    payment_products = ensure_default_payment_products(db)

    settled = 0
    for spec in SAMPLE_PAYERS:
        payer = ensure_sample_payer(db, admin, role_payer, spec)
        db.commit()
        for obl_spec in spec["obligations"]:
            obl = ensure_obligation(db, payer, obl_spec)
            db.commit()
            if obl_spec.get("settle"):
                txn = settle_obligation_if_needed(
                    db,
                    payer,
                    obl,
                    obl_spec["idempotency_key"],
                    admin.user_id,
                )
                if txn and txn.status == "SETTLED":
                    settled += 1

    failures = ensure_failure_demo_cases(db, admin)
    db.commit()

    return {
        "payers": len(SAMPLE_PAYERS),
        "settled_payments": settled,
        "admin": admin,
        "failure_demos": failures,
        "utilities": utilities,
        "payment_products": payment_products,
    }


def seed_foundation(db) -> None:
    """One-time platform / geography / roles / revenue foundation."""
    platform = Platform(
        platform_code="EASYPAY",
        platform_name="EasyPay",
        legal_name="EasyPay Collection Platform",
        email=DEFAULT_SUPER_ADMIN["email"],
        default_currency="XAF",
    )
    db.add(platform)
    db.flush()

    cm = GeographicUnit(unit_code="CM", unit_name="Cameroon", unit_type="COUNTRY", country_code="CM")
    db.add(cm)
    db.flush()
    sw = GeographicUnit(
        parent_id=cm.geographic_unit_id,
        unit_code="CM-SW",
        unit_name="Southwest",
        unit_type="REGION",
        country_code="CM",
    )
    db.add(sw)
    db.flush()
    meme = GeographicUnit(
        parent_id=sw.geographic_unit_id,
        unit_code="CM-SW-MEME",
        unit_name="Meme",
        unit_type="DIVISION",
        country_code="CM",
    )
    db.add(meme)
    db.flush()
    kumba = GeographicUnit(
        parent_id=meme.geographic_unit_id,
        unit_code="CM-SW-MEME-KUMBA",
        unit_name="Kumba",
        unit_type="TOWN",
        country_code="CM",
    )
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
            phone_number=f"2337{tcode[-1]}00001",
            momo_number=f"67010000{tcode[-1]}",
            bank_account_number=f"10001{tcode[-1]}9988",
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

    for t, _g in tenants:
        existing = db.query(User).filter(User.username == f"{t.tenant_code.lower()}_admin").first()
        if existing:
            continue
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

    for code, name in [
        ("MOBILE_MONEY", "Mobile Money"),
        ("BANK", "Bank Transfer"),
        ("CARD", "Card"),
        ("OTHER", "Other"),
    ]:
        if not db.query(PaymentChannel).filter(PaymentChannel.code == code).first():
            db.add(PaymentChannel(code=code, name=name))

    for t, g in tenants:
        for code, name, amt in REVENUE_DEFS:
            if db.query(RevenueType).filter(RevenueType.tenant_id == t.tenant_id, RevenueType.code == code).first():
                continue
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

    db.commit()
    ensure_providers(db, admin)
    ensure_notification_toggles(db)


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        fresh = db.query(Platform).first() is None
        if fresh:
            seed_foundation(db)
            print("Foundation seed complete.")
        else:
            print("Foundation already present — ensuring sample data.")

        stats = ensure_sample_demo_data(db)
        admin = stats["admin"]
        settled_count = db.query(Transaction).filter(Transaction.status == "SETTLED").count()
        print("Sample data ready.")
        print(
            f"  SUPER ADMIN: {admin.username} / {DEFAULT_SUPER_ADMIN['password']} "
            f"({admin.email} · {admin.phone_number})"
        )
        print("  Council: kumba1_admin / council123  (also kumba2_admin, kumba3_admin)")
        print("  Payers: abctrading, mambagroceries, buearoasters, threeconner / payer123")
        print(f"  Sample payers ensured: {stats['payers']}")
        print(f"  Settled payments (total in DB): {settled_count}")
        print("  History export: 2 free downloads / fee 500 XAF thereafter")
        print("  PDF branding: platform logo watermark (75% wash) + receipt verify QR via PUBLIC_BASE_URL")
        demos = stats.get("failure_demos") or {}
        if demos:
            print(
                "  Failure demos: "
                f"{demos.get('debit_fail')} (payer debit), "
                f"{demos.get('credit_fail')} (council credit retryable), "
                f"{demos.get('manual')} (manual intervention)"
            )
        utils = stats.get("utilities") or {}
        if utils:
            print(
                "  Utility store: "
                f"ENEO (light), CAMWATER (water) active; DEMO-DISABLED hidden — "
                f"{len(utils)} catalog rows"
            )
        products = stats.get("payment_products") or {}
        if products:
            print(
                "  Payment chooser: "
                f"COUNCIL + UTILITY (+ future via payment_products) — {len(products)} products"
            )
        if fresh:
            print("  Fresh install: ABC Trading has Business License DUE + Waste Levy PAID.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
