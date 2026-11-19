import logging
from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.core.email import queue_funding_intent_email
from app.core.enums import NotificationReferenceTypeEnum, Permission
from app.db.database import get_db
from app.schemas.funding_intent import (
    FundingIntentDeclared,
    FundingIntentDeclaredResponse,
)
from app.services.erp_user import ERPService
from app.utils.auth import require_internal_key

logger = logging.getLogger(__name__)

internal = APIRouter(
    prefix="/internal",
    tags=["Internal"],
    dependencies=[Depends(require_internal_key)],
)

# Staff holding any of these can act on a declared transfer (complete or
# reject it), so they are the ones told that one is waiting.
FUNDING_INTENT_PERMISSIONS = [
    Permission.ADJUST_BALANCE.value,
    Permission.APPROVE_PAYMENTS.value,
    Permission.REJECT_PAYMENTS.value,
]

# Notification.message is String(200)
MAX_MESSAGE_LENGTH = 200


@internal.post(
    "/funding-intents/declared",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=FundingIntentDeclaredResponse,
)
def funding_intent_declared(
    payload: FundingIntentDeclared,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """The core backend reports that a customer says they have sent money.

    Notifies (in-app and by email) everyone who can complete or reject it.
    Idempotent on transactionId, so the core can safely retry.
    """
    if ERPService.has_notification_for_reference(
        db, NotificationReferenceTypeEnum.FUNDING_INTENT, payload.transactionId
    ):
        return FundingIntentDeclaredResponse(notified=0, duplicate=True)

    recipients = ERPService.get_users_with_any_permission(
        db, FUNDING_INTENT_PERMISSIONS
    )
    if not recipients:
        logger.warning(
            "Funding intent %s declared but no staff hold %s, notifying nobody",
            payload.transactionId,
            FUNDING_INTENT_PERMISSIONS,
        )
        return FundingIntentDeclaredResponse(notified=0)

    who = payload.customerName or "A customer"
    message = f"{who} says they sent ₦{payload.amount:,.2f}. Check the bank account."
    ERPService.new_notification(
        db,
        recipients=recipients,
        message=message[:MAX_MESSAGE_LENGTH],
        reference_type=NotificationReferenceTypeEnum.FUNDING_INTENT,
        reference_id=payload.transactionId,
        amount=Decimal(str(payload.amount)),
    )

    for user in recipients:
        queue_funding_intent_email(
            recipient=user.email,
            staff_first_name=user.first_name,
            customer_name=payload.customerName,
            customer_xb_id=payload.customerXbId,
            amount=payload.amount,
            reference=payload.reference,
            background_tasks=background_tasks,
        )

    return FundingIntentDeclaredResponse(notified=len(recipients))
