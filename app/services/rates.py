from uuid import UUID
from fastapi import Depends
import requests
from sqlalchemy.orm import Session

from app.core.base.services import Service
from app.core.enums import RateApprovalRequestTypeEnum
from app.db.database import get_db
from app.schemas.erp.rates import AssetsRequest, AssignAssetsToSegmentRequest, SegmentsBulkUpdateRequest
from app.models.rate_approval_request import RateApprovalRequest
from app.utils.schema import CurrentUser
from app.utils.settings import settings

INTERNAL_KEY = settings.INTERNAL_KEY

class RatesService(Service):
    @staticmethod
    def create_proposal(
        db: Session, 
        type: RateApprovalRequestTypeEnum, 
        payload: dict,
        current_user: CurrentUser
    ):
        new_request = RateApprovalRequest(
            type=type,
            payload=payload,
            requested_by_id=current_user.user.id
        )
        db.add(new_request)
        db.commit()
        db.refresh(new_request)

    @staticmethod
    def get_all_exchange_rates():
        headers = {"x-internal-key": INTERNAL_KEY}
        response = requests.get(
            "https://backend.xbankang.com/internal/wallets/crypto/accepts", headers=headers
        )
        return response.json()
    
    
    @staticmethod
    def post_crypto_rate(request: AssetsRequest):
        response = requests.post(
            "https://backend.xbankang.com/internal/wallets/crypto/accepts", json=request.model_dump(mode="json"), 
            headers={"x-internal-key": INTERNAL_KEY}
        )
        return response.json()
    
    
    @staticmethod
    def update_crypto_rate(
        rate_id: UUID, 
        request: AssetsRequest,
        current_user: CurrentUser,
        db: Session = Depends(get_db)
    ):
        request_dict = request.model_dump(exclude_unset=True, mode="json")

        if 1 == 1:
            proposed_change = RatesService.create_proposal(
                db,
                RateApprovalRequestTypeEnum.ASSET_UPDATE,
                request_dict,
                current_user.user
            )
        
            return {
                "message": "Rate change proposal submitted successfully.",
                "proposed_change": proposed_change
            }

        response = requests.put(
            f"https://backend.xbankang.com/internal/wallets/crypto/accepts/{rate_id}", 
            json=request_dict, 
            headers={"x-internal-key": INTERNAL_KEY}
        )
        return response.json()
    

    @staticmethod    
    def get_all_segments():
        # Implement logic to fetch all segments
        response = requests.get(
            "https://backend.xbankang.com/internal/wallets/crypto/segments",
            headers={"x-internal-key": INTERNAL_KEY}
        )
        return response.json()
    
    @staticmethod
    def bulk_update_segments(
        current_user, 
        request: SegmentsBulkUpdateRequest,
        db: Session = Depends(get_db)
    ):
        request_dict = request.model_dump(mode="json")

        if 1 == 1:
            proposed_change = RatesService.create_proposal(
                db,
                RateApprovalRequestTypeEnum.SEGMENT_UPDATE,
                request_dict,
                current_user.user
            )
        
            return {
                "message": "Segment change proposal submitted successfully.",
                "proposed_change": proposed_change
            }

        response = requests.put(
            "https://backend.xbankang.com/internal/wallets/crypto/segments/bulk",
            json=request_dict,
            headers={"x-internal-key": INTERNAL_KEY}
        )
        return response.json()
    
    @staticmethod
    def bulk_assign_to_segments(
        segment_id: UUID, 
        request: AssignAssetsToSegmentRequest,
        current_user: CurrentUser,
        db: Session = Depends(get_db)
    ):
        request_dict = request.model_dump(mode="json")

        if 1 == 1:
            proposed_change = RatesService.create_proposal(
                db,
                RateApprovalRequestTypeEnum.SEGMENT_UPDATE,
                request_dict,
                current_user.user
            )
        
            return {
                "message": "Rate change proposal submitted successfully.",
                "proposed_change": proposed_change
            }
        
        response = requests.put(
            f"https://backend.xbankang.com/internal/wallets/crypto/segments/{segment_id}/assets/bulk-assign",
            json=request_dict,
            headers={"x-internal-key": INTERNAL_KEY}
        )
        return response.json()
    

    @staticmethod
    def assign_crypto_to_segment(crypto_id: UUID, segment_id: UUID, override_segment: bool):
        response = requests.put(
            f"https://backend.xbankang.com/internal/wallets/crypto/accepts/{crypto_id}",
            json={
                "segmentId": segment_id,
                "overrideSegment": override_segment
            },
            headers={"x-internal-key": INTERNAL_KEY}
        )
        return response.json()