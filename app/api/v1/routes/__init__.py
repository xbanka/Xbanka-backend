from fastapi import APIRouter

from .affiliate import affiliate as affiliate_router
from .auth import auth as auth_router
from .customer import customer as customer_router
from .dashboard import dashboard as dashboard_router
from .erp import erp as erp_router
from .staff import staff as staff_router
from .transaction import transaction as transaction_router

api_version_one = APIRouter(prefix="/api")

api_version_one.include_router(affiliate_router)
api_version_one.include_router(auth_router)
api_version_one.include_router(customer_router)
api_version_one.include_router(dashboard_router)
api_version_one.include_router(erp_router)
api_version_one.include_router(staff_router)
api_version_one.include_router(transaction_router)
