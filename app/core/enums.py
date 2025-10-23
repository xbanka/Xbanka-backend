import enum

class TransactionStatusEnum(str, enum.Enum):
    approved = "approved"
    pending = "pending"
    active = "active"


class PayoutStatusEnum(str, enum.Enum):
    paid = "paid"
    pending = "pending"
    failed = "failed"