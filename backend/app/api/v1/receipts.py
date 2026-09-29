from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import DbDep, UserDep, require_permissions
from app.models.receipt import Receipt
from app.schemas.common import PublicVerifyOut, ReceiptOut
from app.services.payer import get_payer_by_user

router = APIRouter()


class VerifyBody(BaseModel):
    receipt_number: Optional[str] = None
    verification_code: Optional[str] = None


def _mask_name(name: str) -> str:
    if not name:
        return "***"
    parts = name.split()
    masked = []
    for p in parts:
        if len(p) <= 2:
            masked.append(p[0] + "*")
        else:
            masked.append(p[0] + "*" * (len(p) - 2) + p[-1])
    return " ".join(masked)


@router.get("/receipts", response_model=List[ReceiptOut])
def list_receipts(db: DbDep, current: UserDep):
    q = db.query(Receipt)
    if current.user_type == "PAYER":
        payer = get_payer_by_user(db, current.user_id)
        q = q.filter(Receipt.payer_id == payer.payer_id)
    elif current.user_type != "PLATFORM_ADMIN":
        q = q.filter(Receipt.tenant_id == current.tenant_id)
    return q.order_by(Receipt.payment_date.desc()).limit(100).all()


@router.get("/receipts/{receipt_id}", response_model=ReceiptOut)
def get_receipt(receipt_id: str, db: DbDep, current: UserDep):
    r = db.get(Receipt, receipt_id)
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    if current.user_type == "PAYER":
        payer = get_payer_by_user(db, current.user_id)
        if r.payer_id != payer.payer_id:
            raise HTTPException(status_code=403, detail="Forbidden")
    elif current.user_type != "PLATFORM_ADMIN" and r.tenant_id != current.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant isolation")
    return r


@router.post("/receipts/{receipt_id}/revoke")
def revoke_receipt(receipt_id: str, db: DbDep, current = Depends(require_permissions("receipts:revoke"))):
    r = db.get(Receipt, receipt_id)
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    r.status = "REVOKED"
    db.commit()
    return {"message": "Revoked", "receipt_number": r.receipt_number}


@router.get("/public/verify/{token}", response_model=PublicVerifyOut)
def verify_by_token(token: str, db: DbDep):
    r = db.query(Receipt).filter(Receipt.verification_token == token).first()
    return _verify_result(r)


@router.post("/public/verify", response_model=PublicVerifyOut)
def verify_by_body(body: VerifyBody, db: DbDep):
    r = None
    if body.verification_code:
        r = db.query(Receipt).filter(Receipt.verification_token == body.verification_code).first()
    elif body.receipt_number:
        r = db.query(Receipt).filter(Receipt.receipt_number == body.receipt_number).first()
    return _verify_result(r)


def _verify_result(r: Optional[Receipt]) -> PublicVerifyOut:
    if not r:
        return PublicVerifyOut(verified=False, message="RECEIPT NOT VERIFIED — invalid code or does not exist")
    if r.status == "REVOKED":
        return PublicVerifyOut(verified=False, message="RECEIPT NOT VERIFIED — receipt has been revoked")
    return PublicVerifyOut(
        verified=True,
        message="VERIFIED",
        receipt_number=r.receipt_number,
        council_name=r.council_name,
        revenue_name=r.revenue_name,
        amount=r.amount,
        service_fee=r.service_fee,
        total_amount=r.total_amount,
        currency=r.currency,
        payment_date=r.payment_date,
        status=r.status,
        payer_display=_mask_name(r.payer_display_name),
    )
