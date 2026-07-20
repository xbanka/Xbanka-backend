import requests
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.base.services import Service
from app.core.enums import RateApprovalRequestTypeEnum, RatesApprovalStatusEnum
from app.models.rate_change_log import RateChangeLog
from app.schemas.erp.rates import AssetsRequest, AssignAssetsToSegmentRequest, ProposalResponse, RequestUser, SegmentsBulkUpdateRequest
from app.models.rate_approval_request import RateApprovalRequest
from app.utils.schema import CurrentUser
from app.utils.settings import settings

INTERNAL_KEY = settings.INTERNAL_KEY

class RatesService(Service):
    @staticmethod
    def _fetch_current_configuration(type: RateApprovalRequestTypeEnum, target_id: UUID):
        headers = {"x-internal-key": INTERNAL_KEY}
        if type == RateApprovalRequestTypeEnum.ASSET_UPDATE:
            url = f"https://backend.xbankang.com/internal/wallets/crypto/accepts/id/{target_id}"
        else:
            url = f"https://backend.xbankang.com/internal/wallets/crypto/segments/{target_id}"

        response = requests.get(
            url, headers=headers
        )
        if response.status_code == 200:
            result = response.json()
            return result.get("data", {})

        return {}
    
    @staticmethod
    def _fetch_all_assets():
        headers = {"x-internal-key": INTERNAL_KEY}
        response = requests.get(
            "https://backend.xbankang.com/internal/wallets/crypto/accepts", headers=headers
        )
        if response.status_code == 200:
            result = response.json()
            return result.get("data", [])

        return []

    @staticmethod
    def _build_asset_updates(proposal: RateApprovalRequest, current: dict, current_user: CurrentUser):
        payload = proposal.payload if isinstance(proposal.payload, dict) else {}

        return ProposalResponse(
            id=UUID(str(proposal.id)),
            change_type=proposal.type,
            target_id=UUID(str(proposal.target_id)),
            requested_by_id=current_user.user.id,
            requested_by=RequestUser(
                first_name=current_user.user.first_name,
                last_name=current_user.user.last_name,
                role=current_user.user.role.name
            ),
            status=proposal.status,
            created_at=proposal.created_at,
            updated_at=proposal.updated_at,
            previous_configuration=[
                f"Buy: {current.get('buyFeeValue')}%", 
                f"Sell: {current.get('sellFeeValue')}%"
            ],
            new_configuration=[
                f"Buy: {payload.get('buyFeeValue')}%", 
                f"Sell: {payload.get('sellFeeValue')}%"
            ],
            affected_assets=1,
            target=payload.get("name", ""),
            target_currency=payload.get("currency", "")
        )
    
    @staticmethod
    def _build_segment_updates(proposal: RateApprovalRequest, current: dict, current_user: CurrentUser):
        payload = proposal.payload if isinstance(proposal.payload, dict) else {}
        segments = payload.get("segments", [])
        segment = segments[0] if segments else {}

        return ProposalResponse(
            id=UUID(str(proposal.id)),
            change_type=proposal.type,
            target_id=UUID(str(proposal.target_id)),
            requested_by_id=current_user.user.id,
            requested_by=RequestUser(
                first_name=current_user.user.first_name,
                last_name=current_user.user.last_name,
                role=current_user.user.role.name
            ),
            status=proposal.status,
            created_at=proposal.created_at,
            updated_at=proposal.updated_at,
            previous_configuration=[
                f"Buy: {current.get('buySpread')}%", 
                f"Sell: {current.get('sellSpread')}%"
            ],
            new_configuration=[
                f"Buy: {segment.get('buySpread')}%", 
                f"Sell: {segment.get('sellSpread')}%"
            ],
            affected_assets=len(segments),
            target=segment.get("name", ""),
            target_currency=segment.get("currency", "")
        )
    
    @staticmethod
    def _build_segment_assignments(proposal: RateApprovalRequest, current: dict, current_user: CurrentUser):
        payload = proposal.payload if isinstance(proposal.payload, dict) else {}
        asset_ids = payload.get("assetIds", [])

        assets = current.get("assets", [])
        current_assets = [asset.get("currency") for asset in assets]

        # Fetch all available assets
        all_assets = RatesService._fetch_all_assets()
        available_assets = [asset.get("currency") for asset in all_assets if asset.get("id") in set(asset_ids)]

        added = set(available_assets) - set(current_assets)

        return ProposalResponse(
            id=UUID(str(proposal.id)),
            change_type=proposal.type,
            target_id=UUID(str(proposal.target_id)),
            requested_by_id=current_user.user.id,
            requested_by=RequestUser(
                first_name=current_user.user.first_name,
                last_name=current_user.user.last_name,
                role=current_user.user.role.name
            ),
            status=proposal.status,
            created_at=proposal.created_at,
            updated_at=proposal.updated_at,
            previous_configuration=current_assets,
            new_configuration=[
                f"+{asset}" for asset in added
            ],
            affected_assets=len(added),
            target=current.get("name", ""),
            target_currency=payload.get("currency", "")
        )

    @staticmethod
    def _build_response(proposal: RateApprovalRequest, current: dict, current_user: CurrentUser):
        if proposal.type == RateApprovalRequestTypeEnum.ASSET_UPDATE:
            # Handle asset update proposals
            return RatesService._build_asset_updates(proposal, current, current_user)
        elif proposal.type == RateApprovalRequestTypeEnum.SEGMENT_UPDATE:
            # Handle segment update proposals
            return RatesService._build_segment_updates(proposal, current, current_user)
        elif proposal.type == RateApprovalRequestTypeEnum.SEGMENT_ASSIGNMENT:
            # Handle segment assignment proposals
            return RatesService._build_segment_assignments(proposal, current, current_user)
        else:
            raise ValueError(f"Unknown proposal type: {proposal.type}")

    @staticmethod
    def get_proposals(db: Session, current_user: CurrentUser):
        responses = []
        proposals = db.query(RateApprovalRequest).all()
        current = {}

        for proposal in proposals:
            if not proposal.target_id:
                continue  # Skip if target_id is not set

            target_id = UUID(str(proposal.target_id))

            current = RatesService._fetch_current_configuration(proposal.type, target_id) if target_id else {}

            responses.append(
                RatesService._build_response(
                    proposal, 
                    current, 
                    current_user
                )
            )

        return responses
    
    @staticmethod
    def get_raw_proposals(db: Session):
        proposals = db.query(RateApprovalRequest).all()
        return proposals


    @staticmethod
    def create_proposal(
        db: Session, 
        target_id: UUID,
        type: RateApprovalRequestTypeEnum, 
        payload: dict,
        current_user: CurrentUser
    ):
        new_request = RateApprovalRequest(
            type=type,
            target_id=target_id,
            payload=payload,
            requested_by_id=current_user.user.id
        )
        db.add(new_request)
        db.commit()
        db.refresh(new_request)

        return new_request

    @staticmethod
    def get_all_exchange_rates():
        headers = {"x-internal-key": INTERNAL_KEY}
        response = requests.get(
            "https://backend.xbankang.com/internal/wallets/crypto/accepts", headers=headers
        )
        return response.json()
    
    
    @staticmethod
    def post_crypto_rate(db: Session, request: AssetsRequest):
        response = requests.post(
            "https://backend.xbankang.com/internal/wallets/crypto/accepts", json=request.model_dump(mode="json"), 
            headers={"x-internal-key": INTERNAL_KEY}
        )
        return response.json()
    
    
    @staticmethod
    def update_crypto_rate(
        db: Session,
        rate_id: UUID, 
        request: AssetsRequest,
        current_user: CurrentUser
    ):
        request_dict = request.model_dump(exclude_unset=True, mode="json")

        if False:  # Change this to True to enable proposal creation
            proposed_change = RatesService.create_proposal(
                db,
                rate_id,
                RateApprovalRequestTypeEnum.ASSET_UPDATE,
                request_dict,
                current_user
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

        RatesService._log_if_success(
            response, 
            db, 
            rate_id,
            RateApprovalRequestTypeEnum.ASSET_UPDATE,
            request_dict,
            current_user
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
        db: Session,
        current_user, 
        request: SegmentsBulkUpdateRequest,
    ):
        request_dict = request.model_dump(mode="json")

        if False: # Change this to True to enable proposal creation
            for segment in request.segments:
                RatesService.create_proposal(
                    db,
                    segment.id,
                    RateApprovalRequestTypeEnum.SEGMENT_UPDATE,
                    {
                        "setupNote": request.setupNote,
                        "segments": [segment.model_dump(mode="json")]
                    },
                    current_user
                )
        
            return {
                "message": "Segment change proposal submitted successfully.",
            }

        response = requests.put(
            "https://backend.xbankang.com/internal/wallets/crypto/segments/bulk",
            json=request_dict,
            headers={"x-internal-key": INTERNAL_KEY}
        )

        RatesService._log_if_success(
            response, 
            db, 
            None,  # No specific target_id for bulk updates
            RateApprovalRequestTypeEnum.SEGMENT_UPDATE,
            request_dict,
            current_user
        )

        return response.json()
    
    @staticmethod
    def bulk_assign_to_segments(
        db: Session,
        segment_id: UUID, 
        request: AssignAssetsToSegmentRequest,
        current_user: CurrentUser
    ):
        request_dict = request.model_dump(mode="json")

        if False: # Change this to True to enable proposal creation
            proposed_change = RatesService.create_proposal(
                db,
                segment_id, # id of segment assets are assigned to
                RateApprovalRequestTypeEnum.SEGMENT_ASSIGNMENT,
                request_dict,
                current_user
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

        RatesService._log_if_success(
            response, 
            db, 
            segment_id,
            RateApprovalRequestTypeEnum.SEGMENT_ASSIGNMENT,
            request_dict,
            current_user
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


    @staticmethod
    async def approve_proposal(db: Session, proposal_id: UUID, current_user: CurrentUser):
        proposal = db.query(RateApprovalRequest).filter(RateApprovalRequest.id == proposal_id).first()
        if not proposal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Proposal not found"
            )

        if proposal.status != RatesApprovalStatusEnum.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Proposal has already been processed"
            )
        
        # call the internal API to apply the changes based on the proposal type
        headers = {"x-internal-key": INTERNAL_KEY}
        json=proposal.payload

        if proposal.type == RateApprovalRequestTypeEnum.ASSET_UPDATE:
            response = requests.put(
                f"https://backend.xbankang.com/internal/wallets/crypto/accepts/{proposal.target_id}",
                json=json,
                headers=headers
            )
        elif proposal.type == RateApprovalRequestTypeEnum.SEGMENT_UPDATE:
            print(f"Applying segment update for target_id: {proposal.target_id} with payload: {json}")
            response = requests.put(
                "https://backend.xbankang.com/internal/wallets/crypto/segments/bulk",
                json=json,
                headers=headers
            )
            print(f"Response from segment update: {response.status_code}, {response.text}")
        elif proposal.type == RateApprovalRequestTypeEnum.SEGMENT_ASSIGNMENT:
            response = requests.put(
                f"https://backend.xbankang.com/internal/wallets/crypto/segments/{proposal.target_id}/assets/bulk-assign",
                json=json,
                headers=headers
            )
        else:
            raise ValueError(f"Unknown proposal type: {proposal.type}")
        
        if response.status_code != 200:
            raise ValueError(f"Failed to apply proposal changes: {response.text}")

        # Implement logic to approve the proposal
        proposal.status = RatesApprovalStatusEnum.APPROVED

        RatesService.create_log(
            db,
            UUID(str(proposal.target_id)) if proposal.target_id else None,
            proposal.type,
            proposal.payload,
            current_user
        )

        db.commit()
        db.refresh(proposal)

        return response.json()
    
    @staticmethod
    def reject_proposal(db: Session, proposal_id: UUID):
        proposal = db.query(RateApprovalRequest).filter(RateApprovalRequest.id == proposal_id).first()
        if not proposal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Proposal not found"
            )

        if proposal.status != RatesApprovalStatusEnum.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Proposal has already been processed"
            )

        # Implement logic to reject the proposal
        proposal.status = RatesApprovalStatusEnum.REJECTED
        db.commit()
        db.refresh(proposal)

        return proposal
    
    @staticmethod
    def create_log(
        db: Session, 
        target_id: UUID | None,
        change_type: RateApprovalRequestTypeEnum,
        payload: dict | list,
        current_user: CurrentUser
    ):
        log_entry = RateChangeLog(
            type=change_type,
            target_id=target_id,
            payload=payload,
            performed_by_id=current_user.user.id
        )
        db.add(log_entry)

        return log_entry
    

    @staticmethod
    def get_rate_change_logs(db: Session, current_user: CurrentUser):
        responses = []
        logs = db.query(RateChangeLog).all()
        current = {}

        for log in logs:
            if not log.target_id:
                continue  # Skip if target_id is not set

            target_id = UUID(str(log.target_id))

            current = RatesService._fetch_current_configuration(log.type, target_id) if target_id else {}

            responses.append(
                RatesService._build_response(
                    log, 
                    current, 
                    current_user
                )
            )

        return responses
    

    @staticmethod
    def _log_if_success(
        response,
        db: Session,
        target_id: UUID | None,
        type: RateApprovalRequestTypeEnum,
        payload: dict | list,
        current_user: CurrentUser
    ):
        if not response.ok:
            return

        RatesService.create_log(
            db,
            target_id,
            type,
            payload,
            current_user
        )

        db.commit()