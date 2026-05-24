import uuid
import time
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from pydantic import BaseModel
import httpx
import structlog
from pathlib import Path

from app.database import get_db
from app.models.conversation import ConversationMessage, ActiveQualification
from app.models.lead import Lead

router = APIRouter()
log = structlog.get_logger()

# Payloads
class SandboxReplyPayload(BaseModel):
    phone: str
    body: str

@router.post('/facebook/v19.0/{phone_id}/messages', tags=["Mock WhatsApp API"])
async def mock_send_message(phone_id: str, request: Request):
    """
    Mock endpoint that intercepts outgoing WhatsApp messages sent by n8n.
    Logs them to the DB as outbound conversation messages.
    """
    payload = await request.json()
    log.info("mock.whatsapp.outbound_intercepted", phone_id=phone_id, payload=payload)
    
    to_number = payload.get("to")
    msg_type = payload.get("type", "text")
    
    if not to_number:
        raise HTTPException(status_code=400, detail="Missing 'to' phone number")
        
    # Format message body based on type
    if msg_type == "template":
        template_name = payload.get("template", {}).get("name", "unknown")
        body_text = f"[Sent Template: {template_name}]"
    else:
        body_text = payload.get("text", {}).get("body", "")
        
    async with get_db() as db:
        # Check if there is an active qualification for this number
        result = await db.execute(
            select(ActiveQualification).where(ActiveQualification.phone == to_number).limit(1)
        )
        active = result.scalars().first()
        
        if active:
            db.add(ConversationMessage(
                lead_id=active.lead_id,
                direction="outbound",
                body=body_text,
                wa_message_id=f"wamid.{uuid.uuid4().hex}"
            ))
            await db.commit()
            log.info("mock.whatsapp.logged_outbound", lead_id=str(active.lead_id), phone=to_number)
        else:
            log.warning("mock.whatsapp.no_active_qualification_for_outbound", phone=to_number)
            
    return {
        "messaging_product": "whatsapp",
        "contacts": [{"input": to_number, "wa_id": to_number}],
        "messages": [{"id": f"wamid.{uuid.uuid4().hex}"}]
    }

@router.get('/whatsapp/sandbox', response_class=HTMLResponse, tags=["Mock WhatsApp Sandbox"])
async def get_sandbox():
    """Serves the WhatsApp Testing Sandbox HTML UI page."""
    html_path = Path(__file__).parent.parent / "templates" / "sandbox.html"
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="sandbox.html template file not found.")

@router.get('/whatsapp/chats', tags=["Mock WhatsApp Sandbox"])
async def get_sandbox_chats():
    """Lists all active qualifications joined with lead info."""
    async with get_db() as db:
        stmt = (
            select(
                ActiveQualification.lead_id,
                ActiveQualification.phone,
                ActiveQualification.created_at,
                Lead.prospect_name,
                Lead.status
            )
            .join(Lead, ActiveQualification.lead_id == Lead.id)
            .order_by(ActiveQualification.created_at.desc())
        )
        
        result = await db.execute(stmt)
        chats = []
        for row in result.all():
            chats.append({
                "id": str(row.lead_id),
                "phone": row.phone,
                "prospect_name": row.prospect_name,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None
            })
        return chats

@router.get('/whatsapp/messages', tags=["Mock WhatsApp Sandbox"])
async def get_sandbox_messages(phone: str):
    """Retrieves conversation message history for a phone number."""
    async with get_db() as db:
        # Find active qualification to get lead_id
        res = await db.execute(
            select(ActiveQualification.lead_id).where(ActiveQualification.phone == phone).limit(1)
        )
        lead_id = res.scalars().first()
        
        if not lead_id:
            return []
            
        # Get messages
        msg_stmt = (
            select(ConversationMessage)
            .where(ConversationMessage.lead_id == lead_id)
            .order_by(ConversationMessage.sent_at.asc())
        )
        msg_res = await db.execute(msg_stmt)
        messages = []
        for msg in msg_res.scalars().all():
            messages.append({
                "id": str(msg.id),
                "direction": msg.direction,
                "body": msg.body,
                "sent_at": msg.sent_at.isoformat() if msg.sent_at else None
            })
        return messages

@router.post('/whatsapp/send-reply', tags=["Mock WhatsApp Sandbox"])
async def send_simulated_reply(payload: SandboxReplyPayload, request: Request):
    """
    Simulates a prospect message by building a Meta-compliant webhook payload
    and POSTing it directly to our app's own /webhook/whatsapp endpoint.
    """
    base_url = str(request.base_url).rstrip('/')
    webhook_url = f"{base_url}/webhook/whatsapp"
    
    mock_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "mock_waba_id",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550000000",
                                "phone_number_id": "mock_phone_number_id"
                            },
                            "contacts": [
                                {
                                    "profile": {
                                        "name": "Simulated User"
                                    },
                                    "wa_id": payload.phone
                                }
                            ],
                            "messages": [
                                {
                                    "from": payload.phone,
                                    "id": f"wamid.mock_{uuid.uuid4().hex}",
                                    "timestamp": str(int(time.time())),
                                    "text": {
                                        "body": payload.body
                                    },
                                    "type": "text"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }
    
    log.info("mock.whatsapp.triggering_webhook", webhook_url=webhook_url, payload_phone=payload.phone)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json=mock_payload)
            resp.raise_for_status()
            return {"status": "ok", "detail": "Simulation successful"}
    except httpx.HTTPError as e:
        log.error("mock.whatsapp.webhook_trigger_failed", error=str(e))
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to post mock payload to local webhook: {str(e)}"
        )
