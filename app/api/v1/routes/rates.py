from uuid import UUID

from fastapi import APIRouter, Depends
from app.schemas.erp.rates import (
    AssignAssetsToSegmentRequest, 
    BulkAssetsResponse, 
    BulkSegmentsResponse, 
    AssetsRequest, 
    BulkUpdateSegmentsResponse, 
    SegmentsBulkUpdateRequest, 
    UpdateAssetResponse
)
from app.services.rates import RatesService
from app.utils.auth import require_roles
from app.utils.schema import CurrentUser


rates = APIRouter(prefix="/rates", tags=["Rates"])

@rates.get("/crypto/all", response_model=BulkAssetsResponse)
def get_crypto_rates(current_user: CurrentUser = Depends(require_roles("erp"))):
    return RatesService.get_all_exchange_rates()


@rates.post("/crypto")
def post_crypto_rate(
    request: AssetsRequest,
    current_user: CurrentUser = Depends(require_roles("erp",))
):
    return RatesService.post_crypto_rate(request)


@rates.put("/crypto/{rate_id}", response_model=UpdateAssetResponse)
def update_crypto_rate(
    rate_id: UUID, 
    request: AssetsRequest,
    current_user: CurrentUser = Depends(require_roles("erp"))
):
    return RatesService.update_crypto_rate(
        rate_id, 
        request,
        current_user
    )


@rates.get("/segments/all", response_model=BulkSegmentsResponse)
def get_all_segments(current_user: CurrentUser = Depends(require_roles("erp"))):
    return RatesService.get_all_segments()


@rates.put("/segments/bulk", response_model=BulkUpdateSegmentsResponse)
def bulk_update_segments(
    request: SegmentsBulkUpdateRequest,
    current_user: CurrentUser = Depends(require_roles("erp")),
):
    return RatesService.bulk_update_segments(current_user, request)


@rates.put("/segments/{segment_id}/bulk-assign", response_model=BulkUpdateSegmentsResponse)
def bulk_assign_segments(
    segment_id: UUID, 
    request: AssignAssetsToSegmentRequest,
    current_user: CurrentUser = Depends(require_roles("erp"))
):
    return RatesService.bulk_assign_to_segments(
        segment_id, 
        request, 
        current_user
    )