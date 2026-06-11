from typing import List

from fastapi import APIRouter
from app.schemas.erp.rates import PostRatesRequest, SegmentSchema
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


@rates.get("/segments/all")
def get_all_segments():
    return RatesService.get_all_segments()


# @rates.put("/segments/bulk")
# def bulk_update_segments(segments: List[SegmentSchema]):
#     return RatesService.bulk_update_segments(segments)


# # assign crypto to segment
# @rates.put("/segments/{segment_id}/assign")
# def assign_crypto_to_segment(segment_id: str, crypto_ids: List[str]):
#     # Implement logic to assign crypto to segment
#     pass

