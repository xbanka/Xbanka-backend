from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.database import get_db
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
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("erp",))
):
    return RatesService.post_crypto_rate(db, request)


@rates.put("/crypto/{rate_id}", 
        #    response_model=UpdateAssetResponse
        )
def update_crypto_rate(
    rate_id: UUID, 
    request: AssetsRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("erp"))
):
    return RatesService.update_crypto_rate(
        db,
        rate_id, 
        request,
        current_user
    )


@rates.get("/segments/all", response_model=BulkSegmentsResponse)
def get_all_segments(current_user: CurrentUser = Depends(require_roles("erp"))):
    return RatesService.get_all_segments()


@rates.put("/segments/bulk", 
        #    response_model=BulkUpdateSegmentsResponse
        )
def bulk_update_segments(
    request: SegmentsBulkUpdateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("erp"))
):
    return RatesService.bulk_update_segments(db, current_user, request)


@rates.put("/segments/{segment_id}/bulk-assign",
        #    response_model=BulkUpdateSegmentsResponse
    )
def bulk_assign_segments(
    segment_id: UUID, 
    request: AssignAssetsToSegmentRequest,
    current_user: CurrentUser = Depends(require_roles("erp")),
    db: Session = Depends(get_db)  
):
    return RatesService.bulk_assign_to_segments(
        db,
        segment_id, 
        request, 
        current_user
    )

@rates.get(
    "/proposals/raw", status_code=status.HTTP_200_OK
)
def get_raw_proposals(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("erp"))
):
    proposals = RatesService.get_raw_proposals(db)

    return {
        "proposals": proposals
    }


@rates.get(
    "/proposals", status_code=status.HTTP_200_OK
)
def view_rate_management_proposals(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("erp"))
):
    proposals = RatesService.get_proposals(db, current_user)

    return {
        "proposals": proposals
    }


# approve rate management proposal
@rates.post(
    "/proposals/{proposal_id}/approve", status_code=status.HTTP_200_OK
)
async def approve_rate_management_proposal(
    proposal_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("erp"))
):
    proposal = await RatesService.approve_proposal(
        db, 
        proposal_id, 
        current_user
    )

    return {
        "message": "Proposal approved successfully",
        "proposal": proposal
    }


# reject rate management proposal
@rates.post(
    "/proposals/{proposal_id}/reject", status_code=status.HTTP_200_OK
)
def reject_rate_management_proposal(
    proposal_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("erp"))
):
    proposal = RatesService.reject_proposal(db, proposal_id)

    return {
        "message": "Proposal rejected successfully",
        "proposal": proposal
    }