from app.schemas.shared import ApiResponse

from datetime import datetime
from pydantic import BaseModel, Field
from pydantic import ConfigDict
from typing import List, Optional
from uuid import UUID

from app.core.enums import RatesApprovalStatusEnum


class RequestUser(BaseModel):
    first_name: str
    last_name: str
    role: str

class AffectedAssetItem(BaseModel):
    id: UUID
    name: str
    currency: str
    previous_configuration: list[str]
    new_configuration: list[str]
    status: str

class ProposalResponse(BaseModel):
    id: UUID
    change_type: str
    target_id: UUID
    requested_by_id: UUID
    requested_by: RequestUser
    performed_by_id: Optional[UUID] = None
    performed_by: Optional[RequestUser] = None
    status: RatesApprovalStatusEnum
    target: str
    target_currency: Optional[str] = None
    previous_configuration: list[str]
    new_configuration: list[str]
    affected_assets: int
    affected_assets_detail: Optional[List[AffectedAssetItem]] = None
    created_at: datetime
    updated_at: datetime


# =========================
# Request Models
# =========================
class AssetsRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    currency: Optional[str] = Field(None, description="The currency code (e.g., USD, EUR)")
    name: Optional[str] = Field(None, description="The name of the currency (e.g., US Dollar, Euro)")
    isActive: Optional[bool] = Field(None, description="Whether the currency is active or not")
    buyFeeType: Optional[str] = Field(None, description="The type of buy fee (e.g., percentage, fixed)")
    buyFeeValue: Optional[float] = Field(None, description="The value of the buy fee")
    sellFeeType: Optional[str] = Field(None, description="The type of sell fee (e.g., percentage, fixed)")
    sellFeeValue: Optional[float] = Field(None, description="The value of the sell fee")
    segmentId: Optional[UUID] = Field(None, description="The id of segment crypto belongs to")


class SegmentRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="The id of segment")
    name: str = Field(..., description="The name of the segment")
    isActive: bool = Field(..., description="Whether the segment is active or not")
    buyFeeType: str = Field(..., description="The type of buy fee (e.g., percentage, fixed)")
    buySpread: float = Field(..., description="The value of the buy spread")
    sellFeeType: str = Field(..., description="The type of sell fee (e.g., percentage, fixed)")
    sellSpread: float = Field(..., description="The value of the sell spread")

class SegmentsBulkUpdateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    segments: List[SegmentRequest]
    setupNote: str = Field(..., description="Note or reason for assigning these assets to the segment")

class AssignAssetsToSegmentRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assetIds: List[str] = Field(..., description="List of asset IDs to assign to the segment")
    setupNote: str = Field(..., description="Note or reason for assigning these assets to the segment")


# =========================
# Shared Response Models
# =========================

class AssetSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    currency: str
    name: str
    isActive: bool
    buyFeeType: str
    buyFeeValue: float
    sellFeeType: str
    sellFeeValue: float
    overrideSegment: bool = False
    segmentId: UUID
    obiexRate: float
    obiexValue: float
    createdAt: datetime
    updatedAt: datetime


class SegmentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    isActive: bool
    buyFeeType: str
    buySpread: float
    sellFeeType: str
    sellSpread: float
    createdAt: datetime
    updatedAt: datetime


# =========================
# Segments Endpoint
# =========================


class SuccessData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    success: bool
    message: str

class SegmentResponse(SegmentSummary):
    assets: List[AssetSummary]

BulkSegmentsResponse = ApiResponse[List[SegmentResponse]]
BulkUpdateSegmentsResponse = ApiResponse[SuccessData]


# =========================
# Assets Endpoint
# =========================

class AssetResponse(AssetSummary):
    segment: SegmentSummary

BulkAssetsResponse = ApiResponse[List[AssetResponse]]
UpdateAssetResponse = ApiResponse[AssetSummary]
