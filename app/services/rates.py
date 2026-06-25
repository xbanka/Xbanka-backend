from typing import List
from uuid import UUID
import requests

from app.core.base.services import Service
from app.schemas.erp.rates import AssetsRequest, AssignAssetsToSegmentRequest, SegmentRequest
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
    
    
    @staticmethod
    def post_crypto_rate(request: AssetsRequest):
        response = requests.post(
            "https://backend.xbankang.com/internal/wallets/crypto/accepts", json=request.model_dump(mode="json"), 
            headers={"x-internal-key": INTERNAL_KEY}
        )
        return response.json()
    
    
    @staticmethod
    def update_crypto_rate(rate_id: UUID, request: AssetsRequest):
        response = requests.put(
            f"https://backend.xbankang.com/internal/wallets/crypto/accepts/{rate_id}", json=request.model_dump(exclude_unset=True, mode="json"), 
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
    def bulk_update_segments(current_user, segments: List[SegmentRequest]):
        response = requests.put(
            "https://backend.xbankang.com/internal/wallets/crypto/segments/bulk",
            json={
                "setupNote": "Update segment margins",
                "segments": [segment.model_dump(mode="json") for segment in segments],
                "user": {
                    "name": current_user.name,
                    "email": current_user.email,
                    "role": current_user.role.name
                }
            },
            headers={"x-internal-key": INTERNAL_KEY}
        )
        return response.json()
    
    @staticmethod
    def bulk_assign_to_segments(segment_id: UUID, request: AssignAssetsToSegmentRequest):
        response = requests.put(
            f"https://backend.xbankang.com/internal/wallets/crypto/segments/{segment_id}/assets/bulk-assign",
            json=request.model_dump(mode="json"),
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