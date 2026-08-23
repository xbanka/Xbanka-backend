from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import (
    NotificationReferenceTypeEnum,
    NotificationStatusEnum,
    NotificationTypeEnum,
)
from app.schemas.affiliate import AffiliateSummaryResponse


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


class NotificationReadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_read: bool
    read_at: datetime | None
