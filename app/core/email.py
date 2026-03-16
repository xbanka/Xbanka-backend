import resend
from typing import Dict

from fastapi import BackgroundTasks, HTTPException, status
from fastapi_mail import FastMail, MessageSchema, MessageType

from app.core.config import conf
from app.core.enums import EmailTypeEnum
from app.utils.settings import settings

AFFILIATE_FRONTEND_URL = settings.AFFILIATE_FRONTEND_URL
ERP_FRONTEND_URL = settings.ERP_FRONTEND_URL
MAIL_FROM = settings.MAIL_FROM
RESEND_API_KEY = settings.RESEND_API_KEY
TEST_EMAIL = settings.TEST_EMAIL


resend.api_key = RESEND_API_KEY

# Mapping ensures easier extension later

url_map = {
    EmailTypeEnum.affiliate: AFFILIATE_FRONTEND_URL,
    EmailTypeEnum.erp: ERP_FRONTEND_URL,
}


async def send_verification_email(
    recipient: str,
    email_type: EmailTypeEnum,
    first_name: str,
    last_name: str,
    verification_url: str,
    background_tasks: BackgroundTasks,
):

    template_map = {
        EmailTypeEnum.affiliate: "email_template_affiliates.html",
        EmailTypeEnum.erp: "email_template_erp.html",
    }

    email_template = template_map.get(email_type)
    template_url = url_map.get(email_type)

    if not template_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Environment variable for frontend URL is missing",
        )

    template_body: Dict[str, str] = {
        "first_name": first_name,
        "last_name": last_name,
        "verification_url": verification_url,
        "frontend_url": template_url,
    }

    message = MessageSchema(
        subject="Verify Your Email Address",
        recipients=[recipient],
        template_body=template_body,
        subtype=MessageType.html,
    )

    if settings.DEBUG:
        message.recipients.append(TEST_EMAIL)

    fm = FastMail(conf)
    # await fm.send_message(message, template_name='email_template.html')
    background_tasks.add_task(fm.send_message, message, email_template)


async def send_forgot_password_email(
    recipient: str,
    email_type: EmailTypeEnum,
    first_name: str,
    last_name: str,
    reset_url: str,
    background_tasks: BackgroundTasks,
):
    
    template_url = url_map.get(email_type)
    
    params: resend.Emails.SendParams = {
        "from": "xbankang.com@xbankang.com",
        "to": [recipient],
        "subject": "Reset Your Password",
        "template": {
            "id": "ffaff905-1e5b-499d-aa15-706004736296",
            "variables": {
                "first_name": first_name,
                "last_name": last_name,
                "reset_url": reset_url,
                "frontend_url": template_url,
                "year": 2026,
            },
        },
    }

    email = resend.Emails.send(params)
    print(f"Email sent: {email}")

    # template_url = url_map.get(email_type)

    # if not template_url:
    #     raise HTTPException(
    #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #         detail="Environment variable for frontend URL is missing",
    #     )

    # template_body: Dict[str, str] = {
    #     "first_name": first_name,
    #     "last_name": last_name,
    #     "reset_url": reset_url,
    #     "frontend_url": template_url,
    # }

    # message = MessageSchema(
    #     subject="Reset Your Password",
    #     recipients=[recipient],
    #     template_body=template_body,
    #     subtype=MessageType.html,
    # )

    # fm = FastMail(conf)
    # # await fm.send_message(message, template_name='forgot_password_template.html')
    # background_tasks.add_task(fm.send_message, message, "forgot_password_template.html")


async def send_invite_email(
    recipient: str, signup_url: str, background_tasks: BackgroundTasks
):

    template_body: Dict[str, str] = {
        "signup_url": signup_url,
    }

    message = MessageSchema(
        subject="You're Invited to Join Xbanka ERP",
        recipients=[recipient],
        template_body=template_body,
        subtype=MessageType.html,
    )

    if settings.DEBUG:
        message.recipients.append(TEST_EMAIL)

    fm = FastMail(conf)
    # await fm.send_message(message, template_name='email_template.html')
    background_tasks.add_task(fm.send_message, message, "invite.html")
