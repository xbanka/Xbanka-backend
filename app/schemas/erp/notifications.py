from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.core.enums import NotificationTypeEnum
from app.schemas.erp.user import UserBase

class NotificationsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)


    id: UUID
    message: str
    type: NotificationTypeEnum
    is_read: bool
    read_at: datetime | None
    user: UserBase


class NotificationReadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_read: bool
    read_at: datetime | None
