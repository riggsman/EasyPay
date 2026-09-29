from fastapi import APIRouter

from app.api.v1 import auth, geography, tenants, platforms, payers, revenue, obligations, payments, receipts, settlements, reports, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(platforms.router, tags=["platforms"])
api_router.include_router(geography.router, tags=["geography"])
api_router.include_router(tenants.router, tags=["tenants"])
api_router.include_router(users.router, tags=["users"])
api_router.include_router(payers.router, tags=["payers"])
api_router.include_router(revenue.router, tags=["revenue"])
api_router.include_router(obligations.router, tags=["obligations"])
api_router.include_router(payments.router, tags=["payments"])
api_router.include_router(receipts.router, tags=["receipts"])
api_router.include_router(settlements.router, tags=["settlements"])
api_router.include_router(reports.router, tags=["reports"])
