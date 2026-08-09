import requests
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.base.services import Service
from app.core.enums import (
    NotificationReferenceTypeEnum,
    Permission as PermissionEnum,
    RateApprovalRequestTypeEnum,
    RatesApprovalStatusEnum,
)
from app.models.rate_change_log import RateChangeLog
from app.schemas.erp.rates import AffectedAssetItem, AssetsRequest, AssignAssetsToSegmentRequest, ProposalResponse, RequestUser, SegmentsBulkUpdateRequest
from app.models.rate_approval_request import RateApprovalRequest
from app.services.erp_user import ERPService
from app.utils.schema import CurrentUser
from app.utils.settings import settings

INTERNAL_KEY = settings.INTERNAL_KEY

class RatesService(Service):
    @staticmethod
    def _fetch_current_state():
        all_assets = RatesService._fetch_all_assets()
        all_segments = RatesService._fetch_segments()

        return {
            "assets": {
                asset["id"]: asset
                for asset in all_assets
            },
            "segments": {
                segment["id"]: segment
                for segment in all_segments
            }
        }

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
    def _fetch_segments():
        headers = {"x-internal-key": INTERNAL_KEY}
        response = requests.get(
            "https://backend.xbankang.com/internal/wallets/crypto/segments",
            headers=headers
        )
        if response.status_code == 200:
            result = response.json()
            return result.get("data", [])

        return []

    @staticmethod
    def _fetch_segment_assets(segment_id: UUID) -> list[dict]:
        """Assets currently assigned to a segment and inheriting its spread (not overridden). Live lookup."""
        segment_key = str(segment_id)
        return [
            asset for asset in RatesService._fetch_all_assets()
            if str(asset.get("segmentId")) == segment_key and not asset.get("overrideSegment", False)
        ]

    @staticmethod
    def _build_snapshot(type: RateApprovalRequestTypeEnum, target_id: UUID, payload: dict, current_state: dict):
        """Compute the previous/new configuration snapshot for a proposal, once, at creation time."""
        target_key = str(target_id)

        if type == RateApprovalRequestTypeEnum.ASSET_UPDATE:
            asset = current_state["assets"].get(target_key, {})
            previous = {
                "buyFeeValue": asset.get("buyFeeValue"),
                "sellFeeValue": asset.get("sellFeeValue"),
                "isActive": asset.get("isActive"),
            }
            new = {**previous, **{k: v for k, v in payload.items() if k in previous}}
            return {
                "previous_configuration": previous,
                "new_configuration": new,
                "target_label": asset.get("name", ""),
                "target_currency": asset.get("currency"),
                "affected_assets": 1,
            }

        if type == RateApprovalRequestTypeEnum.SEGMENT_UPDATE:
            segment = current_state["segments"].get(target_key, {})
            proposed_segments = payload.get("segments", [])
            proposed = proposed_segments[0] if proposed_segments else {}
            previous = {
                "name": segment.get("name"),
                "buySpread": segment.get("buySpread"),
                "sellSpread": segment.get("sellSpread"),
                "isActive": segment.get("isActive"),
            }
            new = {**previous, **{k: v for k, v in proposed.items() if k in previous}}
            return {
                "previous_configuration": previous,
                "new_configuration": new,
                "target_label": new.get("name", ""),
                "target_currency": proposed.get("currency"),
                "affected_assets": len(proposed_segments),
            }

        if type == RateApprovalRequestTypeEnum.SEGMENT_ASSIGNMENT:
            asset = current_state["assets"].get(target_key, {})
            current_segment = asset.get("segment") or {}
            destination_segment = current_state["segments"].get(str(payload.get("segmentId")), {})
            previous = {
                "name": current_segment.get("name"),
                "buySpread": current_segment.get("buySpread"),
                "sellSpread": current_segment.get("sellSpread"),
                "isActive": current_segment.get("isActive"),
            }
            new = {
                "name": destination_segment.get("name"),
                "buySpread": destination_segment.get("buySpread"),
                "sellSpread": destination_segment.get("sellSpread"),
                "isActive": destination_segment.get("isActive"),
            }
            return {
                "previous_configuration": previous,
                "new_configuration": new,
                "target_label": asset.get("name", ""),
                "target_currency": asset.get("currency"),
                "affected_assets": 1,
            }

        raise ValueError(f"Unknown proposal type: {type}")

    @staticmethod
    def _format_configuration(
        change_type: RateApprovalRequestTypeEnum, previous_config: dict, new_config: dict
    ) -> tuple[list[str], list[str]]:
        """Format previous/new configuration snapshots into aligned display string lists.
        Buy/sell always show; active status only shows when it actually changed."""
        previous_config = previous_config or {}
        new_config = new_config or {}

        if change_type == RateApprovalRequestTypeEnum.ASSET_UPDATE:
            previous_lines = [
                f"Buy: {previous_config.get('buyFeeValue')}%",
                f"Sell: {previous_config.get('sellFeeValue')}%",
            ]
            new_lines = [
                f"Buy: {new_config.get('buyFeeValue')}%",
                f"Sell: {new_config.get('sellFeeValue')}%",
            ]
        elif change_type in (
            RateApprovalRequestTypeEnum.SEGMENT_UPDATE,
            RateApprovalRequestTypeEnum.SEGMENT_ASSIGNMENT,
        ):
            previous_lines = [
                f"Segment: {previous_config.get('name')}",
                f"Buy: {previous_config.get('buySpread')}%",
                f"Sell: {previous_config.get('sellSpread')}%",
            ]
            new_lines = [
                f"Segment: {new_config.get('name')}",
                f"Buy: {new_config.get('buySpread')}%",
                f"Sell: {new_config.get('sellSpread')}%",
            ]
        else:
            return [], []

        if previous_config.get("isActive") != new_config.get("isActive"):
            previous_lines.append(f"Status: {'Active' if previous_config.get('isActive') else 'Inactive'}")
            new_lines.append(f"Status: {'Active' if new_config.get('isActive') else 'Inactive'}")

        return previous_lines, new_lines

    @staticmethod
    def _to_proposal_response(row, actor, include_asset_breakdown: bool = False) -> ProposalResponse:
        """Format a stored RateApprovalRequest/RateChangeLog row using its persisted snapshot. No live fetch,
        except when include_asset_breakdown is set for a SEGMENT_UPDATE row (single-log detail view only)."""
        previous_strings, new_strings = RatesService._format_configuration(
            row.type, row.previous_configuration, row.new_configuration
        )

        affected_assets = row.affected_assets
        affected_assets_detail = None

        if include_asset_breakdown and row.type == RateApprovalRequestTypeEnum.SEGMENT_UPDATE:
            segment_assets = RatesService._fetch_segment_assets(row.target_id)
            affected_assets_detail = [
                AffectedAssetItem(
                    id=UUID(str(asset["id"])),
                    name=asset.get("name", ""),
                    currency=asset.get("currency", ""),
                    previous_configuration=previous_strings,
                    new_configuration=new_strings,
                    status="Updated"
                )
                for asset in segment_assets
            ]
            affected_assets = len(affected_assets_detail)

        return ProposalResponse(
            id=UUID(str(row.id)),
            change_type=row.type,
            target_id=UUID(str(row.target_id)),
            requested_by_id=actor.id,
            requested_by=RequestUser(
                first_name=actor.first_name,
                last_name=actor.last_name,
                role=actor.role.name
            ),
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
            previous_configuration=previous_strings,
            new_configuration=new_strings,
            affected_assets=affected_assets,
            affected_assets_detail=affected_assets_detail,
            target=row.target_label,
            target_currency=row.target_currency,
        )

    @staticmethod
    def get_proposals(db: Session, current_user: CurrentUser):
        proposals = db.query(RateApprovalRequest).all()

        return [
            RatesService._to_proposal_response(proposal, proposal.requested_by)
            for proposal in proposals
            if proposal.target_id
        ]

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
        current_user: CurrentUser,
        current_state: dict | None = None
    ):
        current_state = current_state if current_state is not None else RatesService._fetch_current_state()
        snapshot = RatesService._build_snapshot(type, target_id, payload, current_state)

        new_request = RateApprovalRequest(
            type=type,
            target_id=target_id,
            payload=payload,
            requested_by_id=current_user.user.id,
            **snapshot
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

        proposed_change = RatesService.create_proposal(
            db,
            rate_id,
            RateApprovalRequestTypeEnum.ASSET_UPDATE,
            request_dict,
            current_user
        )

        ERPService.notify_permission_holders(
            db,
            PermissionEnum.APPROVE_RATE_CHANGES,
            exclude_user_id=current_user.user.id,
            message="Rate change proposal submitted for review",
            reference_type=NotificationReferenceTypeEnum.RATE_PROPOSAL,
            reference_id=proposed_change.id,
        )

        return {
            "message": "Rate change proposal submitted successfully.",
            "proposed_change": proposed_change
        }


    @staticmethod
    def get_all_segments():
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
        current_state = RatesService._fetch_current_state()

        for segment in request.segments:
            RatesService.create_proposal(
                db,
                segment.id,
                RateApprovalRequestTypeEnum.SEGMENT_UPDATE,
                {
                    "setupNote": request.setupNote,
                    "segments": [segment.model_dump(mode="json")]
                },
                current_user,
                current_state
            )

        ERPService.notify_permission_holders(
            db,
            PermissionEnum.APPROVE_RATE_CHANGES,
            exclude_user_id=current_user.user.id,
            message=f"Segment update proposal submitted for {len(request.segments)} segment(s)",
            reference_type=NotificationReferenceTypeEnum.RATE_PROPOSAL,
        )

        return {
            "message": "Segment change proposal submitted successfully.",
        }

    @staticmethod
    def bulk_assign_to_segments(
        db: Session,
        segment_id: UUID,
        request: AssignAssetsToSegmentRequest,
        current_user: CurrentUser
    ):
        # since assetId is the target id, reconstruct payload to include segmentId discarding assetIds
        request_dict = {
            "segmentId": str(segment_id),
            "setupNote": request.setupNote
        }

        current_state = RatesService._fetch_current_state()

        for assetId in request.assetIds:
            RatesService.create_proposal(
                db,
                UUID(assetId),  # id of asset being reassigned
                RateApprovalRequestTypeEnum.SEGMENT_ASSIGNMENT,
                request_dict,
                current_user,
                current_state
            )

        ERPService.notify_permission_holders(
            db,
            PermissionEnum.APPROVE_RATE_CHANGES,
            exclude_user_id=current_user.user.id,
            message=f"Segment assignment proposal submitted for {len(request.assetIds)} asset(s)",
            reference_type=NotificationReferenceTypeEnum.RATE_PROPOSAL,
            reference_id=segment_id,
        )

        return {
            "message": "Rate change proposal submitted successfully.",
        }


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
        payload = proposal.payload

        if proposal.type == RateApprovalRequestTypeEnum.ASSET_UPDATE:
            response = requests.put(
                f"https://backend.xbankang.com/internal/wallets/crypto/accepts/{proposal.target_id}",
                json=payload,
                headers=headers
            )
        elif proposal.type == RateApprovalRequestTypeEnum.SEGMENT_UPDATE:
            response = requests.put(
                "https://backend.xbankang.com/internal/wallets/crypto/segments/bulk",
                json=payload,
                headers=headers
            )
        elif proposal.type == RateApprovalRequestTypeEnum.SEGMENT_ASSIGNMENT:
            if not isinstance(payload, dict):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Expected payload to be of dictionary type"
                )
            response = requests.put(
                f"https://backend.xbankang.com/internal/wallets/crypto/segments/{payload['segmentId']}/assets/bulk-assign",
                json={
                    "assetIds": [str(proposal.target_id)],
                    "setupNote": payload["setupNote"]
                },
                headers=headers
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown proposal type: {proposal.type}"
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to apply proposal changes: {response.text}"
            )

        # Implement logic to approve the proposal
        proposal.status = RatesApprovalStatusEnum.APPROVED

        RatesService.create_log(db, proposal, current_user)

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
        proposal: RateApprovalRequest,
        current_user: CurrentUser
    ):
        """Freeze a copy of the approved proposal's snapshot into the audit log. Never recomputed later."""
        log_entry = RateChangeLog(
            type=proposal.type,
            target_id=proposal.target_id,
            payload=proposal.payload,
            previous_configuration=proposal.previous_configuration,
            new_configuration=proposal.new_configuration,
            target_label=proposal.target_label,
            target_currency=proposal.target_currency,
            affected_assets=proposal.affected_assets,
            performed_by_id=current_user.user.id
        )
        db.add(log_entry)

        return log_entry


    @staticmethod
    def get_rate_change_logs(db: Session, current_user: CurrentUser):
        logs = db.query(RateChangeLog).all()

        return [
            RatesService._to_proposal_response(log, log.performed_by)
            for log in logs
            if log.target_id
        ]


    @staticmethod
    def get_log_by_id(log_id: UUID, db: Session, current_user: CurrentUser):
        log = db.get(RateChangeLog, log_id)

        if not log or not log.target_id:
            if not log:
                detail = f"Rate change log with id '{log_id}' not found."
            else:
                detail = (
                    f"Rate change log '{log_id}' exists but has no target_id set; "
                    "unable to determine target configuration."
                )

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail
            )

        return RatesService._to_proposal_response(log, log.performed_by, include_asset_breakdown=True)
