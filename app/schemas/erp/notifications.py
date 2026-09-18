from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import (
    NotificationActionTypeEnum,
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
