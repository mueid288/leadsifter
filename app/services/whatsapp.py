"""
WhatsApp qualification service — pure orchestration, no third-party imports.

Responsibility: look up the active qualification, persist the inbound message,
and delegate the workflow resume to an IWorkflowPort.
"""
import structlog
from sqlalchemy import select

from app.database import get_db
from app.models.conversation import ConversationMessage, ActiveQualification
from app.ports.workflow import IWorkflowPort

log = structlog.get_logger()


async def handle_incoming_message(
    wa_message_id: str,
    from_number: str,
    body: str,
    timestamp: str,
    workflow: IWorkflowPort | None = None,
) -> None:
    # Lazy import to avoid a circular dependency at module load time.
    # container → adapters → config, so importing at call time is clean.
    if workflow is None:
        from app.container import workflow as _default_workflow
        workflow = _default_workflow

    async with get_db() as db:
        # 1. Find the active qualification for this phone number
        result = await db.execute(
            select(ActiveQualification)
            .where(ActiveQualification.phone == from_number)
            .limit(1)
        )
        active = result.scalars().first()

        if not active:
            log.warning("whatsapp.no_active_qualification", phone=from_number)
            return

        # 2. Persist the inbound message to conversation history
        db.add(ConversationMessage(
            lead_id=active.lead_id,
            direction="inbound",
            wa_message_id=wa_message_id,
            body=body,
        ))
        await db.commit()

        # 3. Delegate the n8n resume to the workflow port
        await workflow.resume_execution(active.execution_id, body, from_number)
