from fastapi import APIRouter

from .customer import customer_v2
from .transaction import transaction_v2

api_version_two = APIRouter(prefix="/api/v2")

api_version_two.include_router(customer_v2)
api_version_two.include_router(transaction_v2)
