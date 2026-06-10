from fastapi import APIRouter
from app.schemas.erp.rates import PostRatesRequest
from app.services.rates import RatesService


rates = APIRouter(prefix="/rates", tags=["Rates"])

@rates.get("/crypto/all")
def get_crypto_rates():
    return RatesService.get_all_exchange_rates()


@rates.post("/crypto")
def post_crypto_rate(request: PostRatesRequest):
    return RatesService.post_crypto_rate(request)


@rates.put("/crypto/{rate_id}")
def update_crypto_rate(rate_id: str, request: PostRatesRequest):
    return RatesService.update_crypto_rate(rate_id, request)

