import enum


class AuthProviderEnum(str, enum.Enum):
    email = "email"
    google = "google"

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
    FLAG_TRANSACTIONS = "transactions:flag"
    FREEZE_TRANSACTIONS = "transactions:freeze"
    UPDATE_TRANSACTION_STATUS = "transactions:update_status"
    MARK_TRANSACTION_COMPLETED = "transactions:mark_completed"
    VIEW_ASSIGNED_TRANSACTIONS = "transactions:view_assigned"
    VIEW_LIMITED_TRANSACTIONS = "transactions:view_limited"
    EXECUTE_TRANSACTIONS = "transactions:execute"
    EDIT_TRANSACTIONS = "transactions:edit"
    MERGE_TRANSACTIONS = "transactions:merge"
    RECOMMEND_TRANSACTION_REVERSAL = "transactions:recommend_reversal"

    # Customers
    VIEW_CUSTOMERS = "customers:view"
    MANAGE_CUSTOMERS = "customers:manage"
    MANAGE_KYC = "customers:manage_kyc"
    FLAG_CUSTOMERS = "customers:flag"
    VIEW_ASSIGNED_CUSTOMERS = "customers:view_assigned"
    UPDATE_CUSTOMERS = "customers:update"
    EDIT_CUSTOMERS = "customers:edit"
    ADD_CUSTOMERS = "customers:add"

    # Finance
    VIEW_PAYMENTS = "finance:view_payments"
    APPROVE_PAYMENTS = "finance:approve_payments"
    REJECT_PAYMENTS = "finance:reject_payments"
    FLAG_PAYMENTS = "finance:flag_payments"
    HOLD_PAYMENTS = "finance:hold_payments"
    RELEASE_PAYMENTS = "finance:release_payments"
    ADJUST_BALANCE = "finance:adjust_balance"
    BYPASS_APPROVALS = "finance:bypass_approvals"
    VIEW_PROFIT = "finance:view_profit"
    REVERSE_SETTLEMENTS = "finance:reverse_settlements"
    RETRY_PAYMENTS = "finance:retry_payments"
    EXPORT_FINANCE_REPORTS = "finance:export_reports"
    VIEW_FINANCE_SUMMARIES = "finance:view_summaries"

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

    # Tasks
    VIEW_TASKS = "tasks:view"
    CREATE_TASKS = "tasks:create"
    ASSIGN_TASKS = "tasks:assign"
    UPDATE_TASK_STATUS = "tasks:update_status"
    VIEW_TASK_PROGRESS = "tasks:view_progress"
    VIEW_TASK_ANALYTICS = "tasks:view_analytics"
    COMMENT_ON_TASKS = "tasks:comment"
    ATTACH_TASK_DOCUMENTS = "tasks:attach_documents"
    CREATE_COMPLIANCE_TASKS = "tasks:create_compliance"
    DELETE_TASKS = "tasks:delete"
    EDIT_TASKS = "tasks:edit"
    VIEW_ASSIGNED_TASKS = "tasks:view_assigned"
    VIEW_TASK_BOARD = "tasks:view_board"

    # Audit
    VIEW_AUDIT_LOGS = "audit:view_logs"
    EXPORT_AUDIT_LOGS = "audit:export_logs"
    BYPASS_AUDIT_LOGGING = "audit:bypass_logging"

    # KYC
    APPROVE_KYC = "kyc:approve"
    REJECT_KYC = "kyc:reject"
    FLAG_KYC = "kyc:flag"
    UPLOAD_KYC_DOCUMENTS = "kyc:upload_documents"
    VIEW_KYC_DATA = "kyc:view_data"
    VIEW_KYC_STATUS = "kyc:view_status"
    UPDATE_KYC_STATUS = "kyc:update_status"
    TOUCH_KYC = "kyc:touch"
    FLAG_KYC_REVIEW = "kyc:flag_review"

    # Affiliate
    VIEW_AFFILIATE_PAYOUTS = "affiliate:view_payouts"
    APPROVE_AFFILIATE_PAYOUTS = "affiliate:approve_payouts"
    HOLD_AFFILIATE_PAYOUTS = "affiliate:hold_payouts"

    # Reconciliation
    VIEW_RECONCILIATION = "reconciliation:view"

    # Dashboard
    VIEW_DASHBOARD = "dashboard:view"

    # Reports
    VIEW_REPORTS = "reports:view"
    EXPORT_OPERATIONAL_REPORTS = "reports:export_operational"
    EXPORT_READONLY_REPORTS = "reports:export_readonly"

    # Records
    DELETE_RECORDS = "records:delete"
    # Rates
    PROPOSE_RATE_CHANGES = "rates:propose_changes"
    APPROVE_RATE_CHANGES = "rates:approve_changes"


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
        Permission.PROPOSE_RATE_CHANGES,
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

class TxnStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RateApprovalRequestTypeEnum(str, enum.Enum):
    ASSET_UPDATE = "ASSET_UPDATE"
    SEGMENT_UPDATE = "SEGMENT_UPDATE"
    SEGMENT_ASSIGNMENT = "SEGMENT_ASSIGNMENT"


class RatesApprovalStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class NotificationReferenceTypeEnum(str, enum.Enum):
    PAYOUT = "PAYOUT"
    RATE_PROPOSAL = "RATE_PROPOSAL"