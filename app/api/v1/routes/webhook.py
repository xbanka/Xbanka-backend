import logging

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import PlainTextResponse

# from app.services.webhook import WebhookService
from app.utils.settings import settings

logger = logging.getLogger(__name__)

webhook = APIRouter(prefix="/webhooks", tags=["Webhook"])

VERIFY_TOKEN = settings.VERIFY_TOKEN


# Meta Verification endpoint


@webhook.get("/whatsapp")
async def whatsapp_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge, status_code=200)

    logger.warning("whatsapp webhook verification failed", extra={"mode": mode})
    raise HTTPException(status_code=403, detail="Verification failed")


# Incoming Messages endpoint


@webhook.post("/whatsapp")
async def whatsapp_webhook_post(request: Request):
    payload = await request.json()
    # Log shape only; payloads carry phone numbers and message text.
    logger.info(
        "whatsapp webhook received",
        extra={
            "object": payload.get("object") if isinstance(payload, dict) else None,
            "entries": len(payload.get("entry", [])) if isinstance(payload, dict) else 0,
        },
    )
    # Process the incoming message as needed
    return {"message": "Webhook received successfully"}
