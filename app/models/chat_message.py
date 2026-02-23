from sqlalchemy import String, Text
from sqlalchemy.orm import mapped_column

from app.models.base_model import BaseModel


class ChatMessage(BaseModel):
    __tablename__ = "chat_messages"

    room_id = mapped_column(String, index=True)
    user_id = mapped_column(String, nullable=False, index=True)
    message = mapped_column(Text, nullable=False)
