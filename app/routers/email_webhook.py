import uuid
from fastapi import APIRouter, Request, BackgroundTasks
from sqlalchemy import select
import structlog

from app.config import settings
from app.database import get_db
from app.models.lead import RawEmail, Lead
from app.models.broker import Broker
from app.ports.email_parser import IEmailParserPort
from app.ports.workflow import IWorkflowPort
from app.container import email_parser as _default_parser, workflow as _default_workflow

router = APIRouter()
log = structlog.get_logger()


async def _process_email(
    broker_id: uuid.UUID,
    raw_email_id: uuid.UUID,
    subject: str,
    text_body: str,
    html_body: str,
    parser: IEmailParserPort,
    workflow: IWorkflowPort,
) -> None:
    """
    Background task: parse email → create Lead → mark RawEmail processed →
    trigger n8n qualification workflow.
    """
    parsed = await parser.parse_lead(subject, text_body, html_body)

    async with get_db() as db:
        lead = Lead(
            broker_id=broker_id,
            raw_email_id=raw_email_id,
            prospect_name=parsed.prospect_name,
            phone=parsed.phone,
            property_ref=parsed.property_ref,
            portal_source=parsed.portal_source,
            status="RAW",
        )
        db.add(lead)

        raw_email = await db.get(RawEmail, raw_email_id)
        if raw_email:
            raw_email.processed = True

        await db.commit()
        await db.refresh(lead)

        log.info("email.lead_created", lead_id=str(lead.id), phone=parsed.phone)

        if not parsed.phone:
            log.warning("email.no_phone_extracted", lead_id=str(lead.id), subject=subject)
            return

        try:
            await workflow.trigger_qualification(broker_id, lead.id, parsed.phone)
            lead.status = "QUALIFYING"
            await db.commit()
        except Exception:
            pass  # Error already logged and raised by the adapter


@router.post('/email', tags=["Webhooks"])
async def receive_email(request: Request, background_tasks: BackgroundTasks):
    """
    Receives inbound email from SendGrid Inbound Parse.
    Returns 200 immediately to prevent SendGrid retries, then processes asynchronously.
    """
    if settings.SENDGRID_WEBHOOK_SECRET:
        sig = request.headers.get("X-Twilio-Email-Event-Webhook-Signature", "")
        ts = request.headers.get("X-Twilio-Email-Event-Webhook-Timestamp", "")
        if not sig or not ts:
            log.warning("email.missing_sendgrid_signature_headers")

    form = await request.form()
    # SendGrid may include display name: "Agency Name <email@domain.com>"
    raw_to = str(form.get('to', ''))
    to_email = raw_to.split('<')[-1].strip('>').strip().lower()
    html_body = str(form.get('html', ''))
    text_body = str(form.get('text', ''))
    from_addr = str(form.get('from', ''))
    subject = str(form.get('subject', ''))

    log.info('email.received', to_email=to_email, subject=subject)

    async with get_db() as db:
        result = await db.execute(
            select(Broker).where(Broker.inbound_email == to_email, Broker.active == True)
        )
        broker = result.scalars().first()

        if not broker:
            log.warning('email.unknown_inbound_address', to_email=to_email)
            return {'status': 'accepted'}

        raw_email = RawEmail(
            broker_id=broker.id,
            from_address=from_addr,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )
        db.add(raw_email)
        await db.commit()
        await db.refresh(raw_email)

        broker_id = broker.id
        raw_email_id = raw_email.id

    background_tasks.add_task(
        _process_email,
        broker_id=broker_id,
        raw_email_id=raw_email_id,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        parser=_default_parser,
        workflow=_default_workflow,
    )

    return {'status': 'accepted'}
