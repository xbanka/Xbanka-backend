from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import PlainTextResponse
# from app.services.webhook import WebhookService
from app.utils.settings import settings

webhook = APIRouter(prefix='/webhooks', tags=['Webhook'])

VERIFY_TOKEN = settings.VERIFY_TOKEN

@webhook.post('/payment')
async def payment_webhook(request: Request):
    payload = await request.json()
    event_type = payload.get('event_type')
    data = payload.get('data')

    if event_type == 'payment_success':
        WebhookService.handle_payment_success(data)
    elif event_type == 'payment_failed':
        WebhookService.handle_payment_failed(data)
    else:
        return {"message": "Event type not supported"}

    return {"message": "Webhook received successfully"}


# Meta Verification endpoint

@webhook.get("/whatsapp")
async def whatsapp_webhook(request: Request):
    mode = request.query_params.get('hub.mode')
    token = request.query_params.get('hub.verify_token')
    challenge = request.query_params.get('hub.challenge')

    if mode == 'subscribe' and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge, status_code=200)
        
    raise HTTPException(status_code=403, detail="Verification failed")


# Incoming Messages endpoint

@webhook.post("/whatsapp")
async def whatsapp_webhook_post(request: Request):
    payload = await request.json()
    print('Received WhatsApp webhook: ', payload)
    # Process the incoming message as needed
    return {"message": "Webhook received successfully"}