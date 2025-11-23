import enum

class TransactionStatusEnum(str, enum.Enum):
    approved = "approved"
    pending = "pending"
    active = "active"


class PayoutStatusEnum(str, enum.Enum):
    paid = "paid"
    pending = "pending"
    failed = "failed"


class NotificationTypeEnum(str, enum.Enum):
    system = "system"
    whatsapp = "whatsapp"


class PayoutMethodEnum(str, enum.Enum):
    bank_transfer = "bank_transfer"
    mobile_money = "mobile_money"

class UserRoleEnum(str, enum.Enum):
    customer_support = "customer_support"


class TicketStatusEnum(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    pending = "pending"


class EmailTypeEnum(str, enum.Enum):
    affiliate = "affiliate"
    erp = "erp"
