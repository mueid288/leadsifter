from fastapi import APIRouter, Request, Query, HTTPException, BackgroundTasks
from app.config import settings
from app.services.whatsapp import handle_incoming_message
from app.models.webhook_log import WebhookLog
from app.database import get_db
import structlog

router = APIRouter()
log = structlog.get_logger()

@router.get('/whatsapp', tags=["Webhooks"])
async def verify_webhook(
    hub_mode: str = Query(alias='hub.mode'),
    hub_verify_token: str = Query(alias='hub.verify_token'),
    hub_challenge: str = Query(alias='hub.challenge'),
):
    """Meta verification handshake"""
    if hub_mode == 'subscribe' and hub_verify_token == settings.META_VERIFY_TOKEN:
        return int(hub_challenge) 
    raise HTTPException(status_code=403, detail='Verification failed')

@router.post('/whatsapp', tags=["Webhooks"])
async def receive_whatsapp(request: Request, background_tasks: BackgroundTasks):
    """Receives WhatsApp events and routes them."""
    payload = await request.json()
    
    async with get_db() as db:
        log_entry = WebhookLog(source='meta_whatsapp', body=payload)
        db.add(log_entry)
        await db.commit()

    try:
        entry = payload['entry'][0]
        changes = entry['changes'][0]
        messages = changes['value'].get('messages', [])
        
        if messages:
            msg = messages[0]
            if msg.get('type') == 'text':
                background_tasks.add_task(
                    handle_incoming_message,
                    wa_message_id=msg['id'],
                    from_number=msg['from'],
                    body=msg['text']['body'],
                    timestamp=msg['timestamp'],
                )
    except (KeyError, IndexError):
        pass # Silently ignore delivery and read receipts
        
    return {'status': 'ok'}
