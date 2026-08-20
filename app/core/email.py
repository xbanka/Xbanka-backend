import logging

import resend
from fastapi import BackgroundTasks, HTTPException, status

from app.core import email_templates
from app.core.enums import EmailTypeEnum
from app.utils.settings import settings

AFFILIATE_FRONTEND_URL = settings.AFFILIATE_FRONTEND_URL
ENVIRONMENT = settings.ENVIRONMENT
ERP_FRONTEND_URL = settings.ERP_FRONTEND_URL
RESEND_API_KEY = settings.RESEND_API_KEY
RESEND_FROM = settings.RESEND_FROM
TEST_EMAIL = settings.TEST_EMAIL

logger = logging.getLogger(__name__)

resend.api_key = RESEND_API_KEY

# Mapping ensures easier extension later

url_map = {
    EmailTypeEnum.affiliate: AFFILIATE_FRONTEND_URL,
    EmailTypeEnum.erp: ERP_FRONTEND_URL,
}

# Shown in the header band, so an ERP message doesn't read as if it came from
# the affiliate product.
product_map = {
    EmailTypeEnum.affiliate: "Xbanka",
    EmailTypeEnum.erp: "Xbanka ERP",
}


def _recipients(recipient: str) -> list[str]:
    """Copy the shared test inbox outside production."""
    if ENVIRONMENT == "development":
        return [recipient, TEST_EMAIL]
    return [recipient]


def _dispatch(subject: str, recipients: list[str], html: str, text: str) -> None:
    """Hand one message to Resend.

    Runs inside a background task because resend.Emails.send is a blocking HTTP
    call — sending it inline would stall the event loop for the whole request.
    Failures are logged rather than raised: the caller's response has already
    gone out by then, and a bounced email should not surface as a 500 on an
    otherwise successful signup.
    """
    params: resend.Emails.SendParams = {
        "from": RESEND_FROM,
        "to": recipients,
        "subject": subject,
        "html": html,
        "text": text,
    }

    try:
        email: resend.Emails.SendResponse = resend.Emails.send(params)
        logger.info("Sent %r to %s (id=%s)", subject, recipients, email.get("id"))
    except Exception:
        logger.exception("Failed to send %r to %s", subject, recipients)


def _resolve_frontend_url(email_type: EmailTypeEnum) -> str:
    template_url = url_map.get(email_type)
    if not template_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Environment variable for frontend URL is missing",
        )
    return template_url


async def send_verification_email(
    recipient: str,
    email_type: EmailTypeEnum,
    first_name: str,
    last_name: str,
    verification_url: str,
    background_tasks: BackgroundTasks,
):
    _resolve_frontend_url(email_type)

    html, text = email_templates.verification_email(
        first_name=first_name,
        last_name=last_name,
        verification_url=verification_url,
        product=product_map.get(email_type, "Xbanka"),
    )

    background_tasks.add_task(
        _dispatch,
        "Verify Your Email Address",
        _recipients(recipient),
        html,
        text,
    )


async def send_forgot_password_email(
    recipient: str,
    email_type: EmailTypeEnum,
    first_name: str,
    last_name: str,
    reset_url: str,
    background_tasks: BackgroundTasks,
):
    _resolve_frontend_url(email_type)

    html, text = email_templates.password_reset_email(
        first_name=first_name,
        last_name=last_name,
        reset_url=reset_url,
        product=product_map.get(email_type, "Xbanka"),
    )

    background_tasks.add_task(
        _dispatch,
        "Reset Your Password",
        _recipients(recipient),
        html,
        text,
    )


async def send_invite_email(
    recipient: str, signup_url: str, background_tasks: BackgroundTasks
):
    html, text = email_templates.staff_invite_email(signup_url=signup_url)

    background_tasks.add_task(
        _dispatch,
        "You're Invited to Join Xbanka ERP",
        _recipients(recipient),
        html,
        text,
    )
