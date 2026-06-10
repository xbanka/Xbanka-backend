from uuid import UUID

import requests
from sqlalchemy.orm import Session

from app.core.base.services import Service
from app.schemas.erp.rates import PostRatesRequest
from app.utils.settings import settings


INTERNAL_KEY = settings.INTERNAL_KEY

class RatesService(Service):
    @staticmethod
    def get_all_exchange_rates():
        headers = {"x-internal-key": INTERNAL_KEY}
        response = requests.get(
            "https://backend.xbankang.com/internal/wallets/crypto/accepts", headers=headers
        )
        return response.json()
    
    
    def post_crypto_rate(request: PostRatesRequest):
        response = requests.post(
            "https://backend.xbankang.com/internal/wallets/crypto/accepts", json=request.model_dump(), 
            headers={"x-internal-key": INTERNAL_KEY}
        )
        return response.json()
    
    
    def update_crypto_rate(rate_id: UUID, request: PostRatesRequest):
        response = requests.put(
            f"https://backend.xbankang.com/internal/wallets/crypto/accepts/{rate_id}", json=request.model_dump(), 
            headers={"x-internal-key": INTERNAL_KEY}
        )
        return response.json()
