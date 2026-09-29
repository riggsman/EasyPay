from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends

from app.core.deps import DbDep, UserDep, require_permissions
from app.schemas.common import DashboardStats
from app.services.payer import get_payer_by_user
from app.services.reporting import collections_report, payer_dashboard, tenant_dashboard

router = APIRouter()


@router.get("/dashboards/payer", response_model=DashboardStats)
def dash_payer(db: DbDep, current: UserDep):
    payer = get_payer_by_user(db, current.user_id)
    return payer_dashboard(db, payer.payer_id)


@router.get("/dashboards/tenant", response_model=DashboardStats)
def dash_tenant(db: DbDep, current = Depends(require_permissions("dashboards:read"))):
    return tenant_dashboard(db, current.tenant_id)


@router.get("/dashboards/platform", response_model=DashboardStats)
def dash_platform(db: DbDep, current = Depends(require_permissions("dashboards:platform"))):
    # Aggregate all tenants for today via empty tenant filter on reporting helpers
    from app.models.transaction import Transaction
    from app.db.base import utcnow
    from datetime import timedelta
    from decimal import Decimal
    from sqlalchemy import func

    start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    collections = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(Transaction.status == "SETTLED", Transaction.settled_at >= start, Transaction.settled_at < end)
        .scalar()
    )
    count = db.query(Transaction).filter(Transaction.initiated_at >= start, Transaction.initiated_at < end).count()
    return DashboardStats(collections_today=Decimal(str(collections)), transactions_today=count)


@router.get("/reports/collections")
def report_collections(
    db: DbDep,
    current = Depends(require_permissions("reports:read")),
    geographic_unit_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
):
    tenant_id = None if current.user_type == "PLATFORM_ADMIN" else current.tenant_id
    return collections_report(
        db,
        tenant_id=tenant_id,
        geographic_unit_id=geographic_unit_id,
        date_from=date_from,
        date_to=date_to,
    )
