from pydantic import BaseModel, ConfigDict

from app.core.enums import NotificationTypeEnum
from app.schemas.erp.user import UserBase

class NotificationsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    type: NotificationTypeEnum
    user: UserBase

