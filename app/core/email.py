from app.core.config import conf
from app.utils.settings import settings
from fastapi import BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, MessageType
from typing import Dict

FRONTEND_URL = settings.FRONTEND_URL

async def send_mail(recipient: str, first_name: str, last_name: str, verification_url: str, background_tasks: BackgroundTasks):
    
    template_body: Dict[str, str] = {
        "first_name": first_name,
        "last_name": last_name,
        "verification_url": verification_url,
        "frontend_url": FRONTEND_URL,
    }

    message = MessageSchema(
        subject="Verify Your Email Address",
        recipients=[recipient],
        template_body= template_body,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    # await fm.send_message(message, template_name='email_template.html')
    background_tasks.add_task(fm.send_message, message, 'email_template.html')
