from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.core.deps import DbDep, UserDep
from app.services.history_exports import generate_history_export, quote_history_export
from app.services.payer import get_payer_by_user

router = APIRouter(prefix="/payers/me/history-exports")


class HistoryExportQuoteOut(BaseModel):
    fee_amount: Decimal
    currency: str
    free_downloads: int
    free_downloads_used: int
    free_downloads_remaining: int
    will_charge: bool
    charge_amount: Decimal


class HistoryExportRequest(BaseModel):
    date_from: datetime
    date_to: datetime
    phone_number: Optional[str] = Field(default=None, description="Required when free allowance is exhausted")


@router.get("/quote", response_model=HistoryExportQuoteOut)
def quote_my_history_export(db: DbDep, current: UserDep):
    if current.user_type != "PAYER":
        raise HTTPException(status_code=403, detail="Payer access only")
    payer = get_payer_by_user(db, current.user_id)
    return HistoryExportQuoteOut(**quote_history_export(db, payer))


@router.post("")
def download_my_history_export(body: HistoryExportRequest, db: DbDep, current: UserDep):
    if current.user_type != "PAYER":
        raise HTTPException(status_code=403, detail="Payer access only")
    payer = get_payer_by_user(db, current.user_id)
    pdf, row, _after = generate_history_export(
        db,
        payer=payer,
        user_id=current.user_id,
        date_from=body.date_from,
        date_to=body.date_to,
        phone_number=body.phone_number,
    )
    filename = f"EasyPay-history-{row.date_from.strftime('%Y%m%d')}-{row.date_to.strftime('%Y%m%d')}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-EasyPay-Export-Id": row.export_id,
            "X-EasyPay-Was-Free": "true" if row.was_free else "false",
            "X-EasyPay-Fee-Amount": str(row.fee_amount),
        },
    )
