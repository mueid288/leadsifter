import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header, Path, BackgroundTasks
from sqlalchemy import select, delete
import structlog

from app.config import settings
from app.database import get_db
from app.models.broker import Broker
from app.models.lead import Lead
from app.models.conversation import ConversationMessage, ActiveQualification
from app.crypto import decrypt
from app.services.lead_injection import inject_lead
from app.schemas.internal import ConversationPayload, LeadStatusPayload, RegisterQualificationPayload

router = APIRouter()
log = structlog.get_logger()

_TERMINAL_STATUSES = {"COLD", "QUALIFIED", "INJECTED", "INJECT_FAILED"}


async def verify_internal_key(x_internal_key: str = Header(...)):
    """Shared secret between FastAPI and n8n. Set via N8N_INTERNAL_KEY env var."""
    if x_internal_key != settings.N8N_INTERNAL_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")
    return True


@router.get('/broker/{broker_id}', dependencies=[Depends(verify_internal_key)])
async def get_broker_credentials(broker_id: uuid.UUID = Path(...)):
    """n8n calls this to get the Meta API Token before sending a WhatsApp message."""
    async with get_db() as db:
        broker = await db.get(Broker, broker_id)
        if not broker:
            raise HTTPException(status_code=404, detail="Broker not found")

        return {
            "meta_token": decrypt(broker.meta_token_enc),
            "phone_id": decrypt(broker.meta_phone_id_enc),
            "agency_name": broker.agency_name,
        }


@router.post('/qualification', dependencies=[Depends(verify_internal_key)])
async def register_qualification(payload: RegisterQualificationPayload):
    """
    n8n calls this immediately before entering a Wait state to record the
    execution_id so that inbound WhatsApp replies can resume the correct workflow.
    Upserts on phone to handle retries gracefully.
    """
    async with get_db() as db:
        result = await db.execute(
            select(ActiveQualification).where(ActiveQualification.phone == payload.phone)
        )
        existing = result.scalars().first()

        if existing:
            existing.execution_id = payload.execution_id
            existing.lead_id = payload.lead_id
            log.info("qualification.updated", phone=payload.phone, execution_id=payload.execution_id)
        else:
            db.add(ActiveQualification(
                phone=payload.phone,
                lead_id=payload.lead_id,
                execution_id=payload.execution_id,
            ))
            log.info("qualification.registered", phone=payload.phone, execution_id=payload.execution_id)

        await db.commit()
    return {"status": "registered"}


@router.post('/conversation', dependencies=[Depends(verify_internal_key)])
async def save_conversation(payload: ConversationPayload):
    """n8n calls this to log the automated messages it sends to the prospect."""
    async with get_db() as db:
        db.add(ConversationMessage(
            lead_id=payload.lead_id,
            direction=payload.direction,
            body=payload.body,
        ))
        await db.commit()
    return {"status": "saved"}


@router.patch('/lead/{lead_id}/status', dependencies=[Depends(verify_internal_key)])
async def update_lead_status(
    lead_id: uuid.UUID = Path(...),
    payload: LeadStatusPayload = None,
    background_tasks: BackgroundTasks = None,
):
    """n8n calls this to mark a lead as COLD, QUALIFIED, etc."""
    if not payload:
        raise HTTPException(status_code=400, detail="Missing payload body")
    if not background_tasks:
        raise HTTPException(status_code=500, detail="BackgroundTasks dependency injection failed")

    async with get_db() as db:
        lead = await db.get(Lead, lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        phone = lead.phone  # capture before any ORM state changes
        lead.status = payload.status
        lead.status_updated_at = datetime.now(timezone.utc)

        # Remove the active qualification record when the lead reaches a terminal state
        if payload.status in _TERMINAL_STATUSES and phone:
            await db.execute(
                delete(ActiveQualification).where(ActiveQualification.phone == phone)
            )
            log.info("qualification.cleaned_up", phone=phone, status=payload.status)

        await db.commit()

        if payload.status == "QUALIFIED":
            background_tasks.add_task(inject_lead, lead_id=lead_id)
            log.info("lead.queued_for_injection", lead_id=str(lead_id))

    return {"status": "updated"}
