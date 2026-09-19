from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, model_validator

from app.core.enums import (
    NotificationActionTypeEnum,
    NotificationCategoryEnum,
    NotificationReferenceTypeEnum,
    NotificationStatusEnum,
    NotificationTypeEnum,
)
from app.schemas.affiliate import AffiliateSummaryResponse


class NotificationAction(BaseModel):
    """An action the recipient can still take from the notification panel.

    Set only while the action is genuinely available - it disappears once the
    underlying record is actioned - so the frontend renders the button on
    `action` rather than guessing from `reference_type`.
    """

    type: NotificationActionTypeEnum
    role_change_id: UUID


class NotificationsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    message: str
    type: NotificationTypeEnum
    is_read: bool
    read_at: Optional[datetime]
    amount: Optional[float]
    method: Optional[str]
    reference_type: NotificationReferenceTypeEnum
    reference_id: Optional[UUID]
    status: NotificationStatusEnum
    affiliate: Optional[AffiliateSummaryResponse] = None
    action: Optional[NotificationAction] = None


class ToggleSet(BaseModel):
    """Both channels for one row of the settings page."""

    in_app: bool
    email: bool


class ToggleSetUpdate(BaseModel):
    """The same pair, partially filled: omitted means "leave as it is"."""

    model_config = ConfigDict(extra="forbid")

    in_app: Optional[bool] = None
    email: Optional[bool] = None


class NotificationPreferencesResponse(BaseModel):
    """Always complete - every category and both channel switches, with
    defaults filled in - so the settings page renders from one call."""

    channels: ToggleSet
    categories: Dict[NotificationCategoryEnum, ToggleSet]


class NotificationPreferencesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channels: Optional[ToggleSetUpdate] = None
    categories: Optional[Dict[NotificationCategoryEnum, ToggleSetUpdate]] = None

    @model_validator(mode="after")
    def _require_a_toggle(self):
        has_channel = self.channels is not None and bool(self.channels.model_fields_set)
        has_category = bool(self.categories) and any(
            bool(toggles.model_fields_set) for toggles in self.categories.values()
        )
        if not (has_channel or has_category):
            raise HTTPException(
                status_code=400,
                detail="Provide at least one channel switch or category toggle.",
            )
        return self


class NotificationCountsResponse(BaseModel):
    all: int
    unread: int


class NotificationReadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_read: bool
    read_at: datetime | None


class TransactionActivityItem(BaseModel):
    id: UUID
    reference: Optional[str] = None
    message: str
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    type: Optional[str] = None
    display_type: Optional[str] = None
    created_at: datetime


class TransactionActivityMeta(BaseModel):
    page: Optional[int] = None
    limit: Optional[int] = None
    totalItems: Optional[int] = None
    totalPages: Optional[int] = None


class TransactionActivityResponse(BaseModel):
    items: List[TransactionActivityItem]
    meta: TransactionActivityMeta
