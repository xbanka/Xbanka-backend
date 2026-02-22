import enum


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


class RoleEnum(str, enum.Enum):
    ADMIN = "Admin"
    MANAGER = "Manager"
    OPERATIONS = "Operations"
    CUSTOMER_REP = "Customer Rep"
    COMPLIANCE = "Compliance"
    VIEWER = "Viewer"


# Define granular permissions organized by category
class Permission(str, enum.Enum):
    # Transactions
    VIEW_TRANSACTIONS = "transactions:view"
    CREATE_TRANSACTIONS = "transactions:create"
    VERIFY_TRANSACTIONS = "transactions:verify"
    SETTLE_TRANSACTIONS = "transactions:settle"
    REFUND_TRANSACTIONS = "transactions:refund"

    # Customers
    VIEW_CUSTOMERS = "customers:view"
    MANAGE_CUSTOMERS = "customers:manage"
    MANAGE_KYC = "customers:manage_kyc"
    FLAG_CUSTOMERS = "customers:flag"

    # Finance
    VIEW_PAYMENTS = "finance:view_payments"
    APPROVE_PAYMENTS = "finance:approve_payments"
    REJECT_PAYMENTS = "finance:reject_payments"
    FLAG_PAYMENTS = "finance:flag_payments"

    # Staff & Access Management
    VIEW_STAFF_LIST = "staff:view_list"
    ADD_STAFF = "staff:add"
    EDIT_STAFF_ROLES = "staff:edit_roles"
    EDIT_STAFF_PERMISSIONS = "staff:edit_permissions"
    SUSPEND_ACTIVATE = "staff:suspend_activate"
    RESET_PASSWORD = "staff:reset_password"
    RESEND_INVITES = "staff:resend_invites"

    # System & Settings
    VIEW_SYSTEM_SETTINGS = "system:view_settings"
    EDIT_SYSTEM_SETTINGS = "system:edit_settings"


# Define job roles with their default permissions
JOB_ROLE_PERMISSIONS = {
    "Admin": set(Permission),  # All permissions
    "Manager": {
        Permission.VIEW_TRANSACTIONS,
        Permission.CREATE_TRANSACTIONS,
        Permission.VERIFY_TRANSACTIONS,
        Permission.SETTLE_TRANSACTIONS,
        Permission.VIEW_CUSTOMERS,
        Permission.MANAGE_CUSTOMERS,
        Permission.MANAGE_KYC,
        Permission.VIEW_PAYMENTS,
        Permission.APPROVE_PAYMENTS,
        Permission.VIEW_STAFF_LIST,
        Permission.ADD_STAFF,
        Permission.EDIT_STAFF_ROLES,
        Permission.VIEW_SYSTEM_SETTINGS,
    },
    "Operations": {
        Permission.VIEW_TRANSACTIONS,
        Permission.CREATE_TRANSACTIONS,
        Permission.VERIFY_TRANSACTIONS,
        Permission.REFUND_TRANSACTIONS,
        Permission.VIEW_CUSTOMERS,
        Permission.MANAGE_KYC,
        Permission.VIEW_PAYMENTS,
    },
    "Customer Rep": {
        Permission.VIEW_TRANSACTIONS,
        Permission.VIEW_CUSTOMERS,
        Permission.MANAGE_CUSTOMERS,
        Permission.MANAGE_KYC,
    },
    "Compliance": {
        Permission.VIEW_TRANSACTIONS,
        Permission.VERIFY_TRANSACTIONS,
        Permission.VIEW_CUSTOMERS,
        Permission.FLAG_CUSTOMERS,
        Permission.VIEW_PAYMENTS,
        Permission.FLAG_PAYMENTS,
    },
    "Viewer": {
        Permission.VIEW_TRANSACTIONS,
        Permission.VIEW_CUSTOMERS,
        Permission.VIEW_PAYMENTS,
        Permission.VIEW_STAFF_LIST,
    },
}
