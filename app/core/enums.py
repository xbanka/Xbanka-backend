import enum

class StatusEnum(str, enum.Enum):
    approved = "approved"
    pending = "pending"
    active = "active"