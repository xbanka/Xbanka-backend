import enum

class TransactionStatusEnum(str, enum.Enum):
    approved = "approved"
    pending = "pending"
    upload_pending = "upload_pending"
    active = "active"


class UploadStatusEnum(str, enum.Enum):
    pending = "pending"
    failed = "failed"
    completed = "completed"


class PayoutStatusEnum(str, enum.Enum):
    paid = "paid"
    pending = "pending"
    failed = "failed"
    rejected = "rejected"


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


class ServiceTypeEnum(str, enum.Enum):
    crypto = "crypto"
    gift_card = "gift_card"
    bill_payments = "bill_payments"


class CryptoPairEnum(str, enum.Enum):
    NGN_USDT = "NGN-USDT"
    USDT_NGN = "USDT-NGN"
    BTC_NGN = "BTC-NGN"
    NGN_BTC = "NGN-BTC"
    ETH_NGN = "ETH-NGN"
    NGN_ETH = "NGN-ETH"
