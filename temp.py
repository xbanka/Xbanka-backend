from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid
import enum

class ConversationStatus(str, enum.Enum):
    open = "open"
    closed = "closed"

class MessageDirection(str, enum.Enum):
    inbound = "inbound"    # customer sent
    outbound = "outbound"  # staff sent

class MessageStatus(str, enum.Enum):
    pending = "pending"      # not yet sent to API
    sent = "sent"            # accepted by Meta
    delivered = "delivered"  # delivered to device
    read = "read"            # customer opened
    failed = "failed"        # rejected/error

class MessageType(str, enum.Enum):
    text = "text"
    image = "image"
    audio = "audio"
    document = "document"
    video = "video"
    template = "template"


class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    whatsapp_number = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)          # from WhatsApp profile
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    conversations = relationship("Conversation", back_populates="customer")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    status = Column(Enum(ConversationStatus), default=ConversationStatus.open, nullable=False)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("staff.id"), nullable=True)  # optional agent assignment
    last_customer_message_at = Column(DateTime(timezone=True), nullable=True)  # 24hr window tracking
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    closed_at = Column(DateTime(timezone=True), nullable=True)

    customer = relationship("Customer", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")
    assigned_staff = relationship("Staff", back_populates="assigned_conversations")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    whatsapp_message_id = Column(String, unique=True, nullable=True, index=True)  # Meta's message ID, for dedup + status updates
    direction = Column(Enum(MessageDirection), nullable=False)
    message_type = Column(Enum(MessageType), default=MessageType.text, nullable=False)
    content = Column(Text, nullable=True)          # text body
    media_url = Column(String, nullable=True)      # stored media path
    media_mime_type = Column(String, nullable=True)
    status = Column(Enum(MessageStatus), default=MessageStatus.pending, nullable=False)
    sent_by = Column(UUID(as_uuid=True), ForeignKey("staff.id"), nullable=True)  # null if inbound
    is_template = Column(Boolean, default=False)
    template_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    failed_reason = Column(String, nullable=True)  # store Meta error if failed

    conversation = relationship("Conversation", back_populates="messages")
    sent_by_staff = relationship("Staff", back_populates="sent_messages")


class Staff(Base):
    __tablename__ = "staff"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    assigned_conversations = relationship("Conversation", back_populates="assigned_staff")
    sent_messages = relationship("Message", back_populates="sent_by_staff")
```

---

### Relationships Visualized
```
Staff ──────────────────────────────────┐
  │                                     │
  │ assigned_to                         │ sent_by
  ▼                                     ▼
Customer ──► Conversation ──► Message
                │
                └── last_customer_message_at  (24hr window)
