from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import mapped_column, relationship

from app.models.base_model import BaseModel


class ChatMessage(BaseModel):
    __tablename__ = "chat_messages"

    room_id = mapped_column(ForeignKey("chat_rooms.id"), nullable=False, index=True)
    chat_room = relationship("ChatRoom", back_populates="chats")
    
    user_id = mapped_column(String, nullable=False, index=True)
    message = mapped_column(Text, nullable=False)
