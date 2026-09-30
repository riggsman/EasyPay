from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

from app.core.deps import DbDep, UserDep, require_permissions
from app.models.receipt import Receipt
from app.schemas.common import PublicVerifyOut, ReceiptOut
from app.schemas.pagination import PaginatedResponse, paginate_query
from app.services.payer import get_payer_by_user
from app.services.receipts_pdf import build_receipt_pdf, receipt_pdf_path

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


def _assert_receipt_access(db, current, receipt: Receipt) -> None:
    if current.user_type == "PAYER":
        payer = get_payer_by_user(db, current.user_id)
        if receipt.payer_id != payer.payer_id:
            raise HTTPException(status_code=403, detail="Forbidden")
    elif current.user_type not in ("PLATFORM_ADMIN", "SUPER_ADMIN") and receipt.tenant_id != current.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant isolation")


def to_receipt_out(receipt: Receipt) -> ReceiptOut:
    data = ReceiptOut.model_validate(receipt).model_dump()
    data["pdf_download_url"] = receipt_pdf_path(receipt.receipt_id)
    return ReceiptOut(**data)


@router.get("/receipts", response_model=PaginatedResponse[ReceiptOut])
def list_receipts(
    db: DbDep,
    current: UserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    status: Optional[str] = None,
    tenant_id: Optional[str] = None,
    q: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
):
    query = db.query(Receipt)
    if current.user_type == "PAYER":
        payer = get_payer_by_user(db, current.user_id)
        query = query.filter(Receipt.payer_id == payer.payer_id)
    elif current.user_type in ("PLATFORM_ADMIN", "SUPER_ADMIN"):
        if tenant_id:
            query = query.filter(Receipt.tenant_id == tenant_id)
    else:
        query = query.filter(Receipt.tenant_id == current.tenant_id)
    if status:
        query = query.filter(Receipt.status == status)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            (Receipt.receipt_number.like(like))
            | (Receipt.council_name.like(like))
            | (Receipt.revenue_name.like(like))
            | (Receipt.payer_display_name.like(like))
        )
    if date_from:
        query = query.filter(Receipt.payment_date >= date_from)
    if date_to:
        query = query.filter(Receipt.payment_date <= date_to)
    query = query.order_by(Receipt.payment_date.desc())
    items, total, total_pages = paginate_query(query, page, page_size)
    return PaginatedResponse(
        items=[to_receipt_out(i) for i in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get("/receipts/{receipt_id}", response_model=ReceiptOut)
def get_receipt(receipt_id: str, db: DbDep, current: UserDep):
    r = db.get(Receipt, receipt_id)
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    _assert_receipt_access(db, current, r)
    return to_receipt_out(r)


@router.get("/receipts/{receipt_id}/pdf")
def download_receipt_pdf(receipt_id: str, db: DbDep, current: UserDep):
    r = db.get(Receipt, receipt_id)
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    _assert_receipt_access(db, current, r)
    if r.status == "REVOKED":
        raise HTTPException(status_code=409, detail="Receipt has been revoked")
    pdf = build_receipt_pdf(db, r)
    filename = f"{r.receipt_number}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/receipts/{receipt_id}/revoke")
def revoke_receipt(receipt_id: str, db: DbDep, current=Depends(require_permissions("receipts:revoke"))):
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
        total_amount=r.total_amount,
        currency=r.currency,
        payment_date=r.payment_date,
        status=r.status,
        payer_display=_mask_name(r.payer_display_name),
        pdf_download_url=None,
    )
