from fastapi import APIRouter

from .affiliate import affiliate as affiliate_router
from .erp import erp as erp_router
from .super_admin import super_admin as super_admin_router

auth = APIRouter(prefix="/auth", tags=["Auth"])

auth.include_router(affiliate_router)
auth.include_router(erp_router)
auth.include_router(super_admin_router)
