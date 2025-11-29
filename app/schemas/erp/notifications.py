from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.core.enums import NotificationTypeEnum
from typing import Optional
from app.schemas.affiliate import AffiliateMeResponse

class NotificationsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)


    id: UUID
    message: str
    type: NotificationTypeEnum
    is_read: bool
    read_at: Optional[datetime]
    bank_name: str
    amount: float
    method: str
    affiliate: AffiliateMeResponse


class NotificationReadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_read: bool
    read_at: datetime | None
