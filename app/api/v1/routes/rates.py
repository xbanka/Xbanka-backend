from typing import List
from uuid import UUID

from fastapi import APIRouter
from app.schemas.erp.rates import BulkAssetsResponse, BulkSegmentsResponse, AssetsRequest, BulkUpdateSegmentsResponse, SegmentRequest, UpdateAssetResponse
from app.services.rates import RatesService


rates = APIRouter(prefix="/rates", tags=["Rates"])

@rates.get("/crypto/all", response_model=BulkAssetsResponse)
def get_crypto_rates():
    return RatesService.get_all_exchange_rates()


@rates.post("/crypto")
def post_crypto_rate(request: AssetsRequest):
    return RatesService.post_crypto_rate(request)


@rates.put("/crypto/{rate_id}", response_model=UpdateAssetResponse)
def update_crypto_rate(rate_id: UUID, request: AssetsRequest):
    return RatesService.update_crypto_rate(rate_id, request)


@rates.get("/segments/all", response_model=BulkSegmentsResponse)
def get_all_segments():
    return RatesService.get_all_segments()


@rates.put("/segments/bulk", response_model=BulkUpdateSegmentsResponse)
def bulk_update_segments(segments: List[SegmentRequest]):
    return RatesService.bulk_update_segments(segments)
