from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models.revenue import CommissionAgreement, FeeBand, FeeConfiguration


def calculate_fee(
    db: Session,
    *,
    amount: Decimal,
    tenant_id: Optional[str],
    geographic_unit_id: Optional[str],
    revenue_type_id: Optional[str],
    payment_channel_code: Optional[str] = None,
) -> Decimal:
    q = db.query(FeeConfiguration).filter(FeeConfiguration.status == "ACTIVE")
    # Prefer most specific match
    configs = q.all()
    best: Optional[FeeConfiguration] = None
    best_score = -1
    for cfg in configs:
        score = 0
        if cfg.tenant_id and cfg.tenant_id != tenant_id:
            continue
        if cfg.geographic_unit_id and cfg.geographic_unit_id != geographic_unit_id:
            continue
        if cfg.revenue_type_id and cfg.revenue_type_id != revenue_type_id:
            continue
        if cfg.tenant_id:
            score += 4
        if cfg.geographic_unit_id:
            score += 2
        if cfg.revenue_type_id:
            score += 1
        if score > best_score:
            best_score = score
            best = cfg

    if not best:
        # Default platform service fee: flat 500 XAF or 1% whichever policy — use flat 500 as SRS example
        return Decimal("500.00") if amount > 0 else Decimal("0")

    bands = db.query(FeeBand).filter(FeeBand.fee_configuration_id == best.fee_configuration_id).all()
    if bands:
        for band in bands:
            if amount >= band.min_amount and (band.max_amount is None or amount <= band.max_amount):
                return _apply(band.fee_type, band.fee_value, amount)
    return _apply(best.fee_type, best.fee_value, amount)


def calculate_commission(
    db: Session,
    *,
    amount: Decimal,
    tenant_id: str,
    revenue_type_id: Optional[str] = None,
) -> Decimal:
    agreements = (
        db.query(CommissionAgreement)
        .filter(CommissionAgreement.tenant_id == tenant_id, CommissionAgreement.status == "ACTIVE")
        .all()
    )
    best = None
    best_score = -1
    for ag in agreements:
        if ag.revenue_type_id and ag.revenue_type_id != revenue_type_id:
            continue
        score = 1 if ag.revenue_type_id else 0
        if score > best_score:
            best_score = score
            best = ag
    if not best:
        return Decimal("0")
    return _apply(best.commission_type, best.commission_value, amount)


def _apply(fee_type: str, value: Decimal, amount: Decimal) -> Decimal:
    if fee_type == "PERCENT":
        return (amount * value / Decimal("100")).quantize(Decimal("0.01"))
    return Decimal(value).quantize(Decimal("0.01"))
