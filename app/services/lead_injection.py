"""
Lead injection service — pure orchestration, no third-party imports.

Responsibility: fetch lead + broker from DB, score the lead, build the
CRMLead value object, delegate to an ICRMPort, and persist the result.

The CRM adapter (PropSpaceAdapter by default) is instantiated here with the
broker's decrypted API key because this service is the only layer that holds
both DB access and the decryption capability simultaneously.
"""
import uuid
from sqlalchemy import select
from sqlalchemy.sql import func
import structlog

from app.config import settings
from app.crypto import decrypt
from app.database import get_db
from app.models.lead import Lead
from app.models.broker import Broker
from app.models.conversation import ConversationMessage
from app.ports.crm import ICRMPort, CRMLead
from app.adapters.propspace import PropSpaceAdapter
from app.services.lead_scorer import score_lead

log = structlog.get_logger()


def _build_transcript(messages: list[ConversationMessage]) -> str:
    return "\n".join(f"[{m.direction.upper()}] {m.body}" for m in messages)


def _build_crm_lead(
    lead: Lead,
    broker: Broker,
    score: str,
    score_reason: str,
    transcript: str,
) -> CRMLead:
    prospect_name = lead.prospect_name or "Portal Inquiry"
    name_parts = prospect_name.split()
    return CRMLead(
        first_name=name_parts[0],
        last_name=" ".join(name_parts[1:]) or "Unknown",
        phone=lead.phone,
        source=f"LeadSifter — {lead.portal_source}",
        notes=(
            f"[LeadSifter Auto-Qualified]\n"
            f"Score: {score} ({score_reason})\n"
            f"Budget: AED {lead.budget_min_aed} – {lead.budget_max_aed}\n"
            f"Timeline: {lead.timeline_days} days\n"
            f"Financing: {lead.financing}\n"
            f"Property: {lead.property_ref}\n\n"
            f"WhatsApp Transcript:\n{transcript}"
        ),
        property_ref=lead.property_ref,
        tag=score,
    )


async def inject_lead(lead_id: uuid.UUID, crm: ICRMPort | None = None) -> None:
    """
    Orchestrate lead injection into the CRM.

    Parameters
    ----------
    lead_id:
        UUID of the lead to inject.
    crm:
        An ICRMPort implementation. If None, PropSpaceAdapter is instantiated
        with the broker's decrypted API key (the default production path).
        Pass a mock adapter in tests.
    """
    async with get_db() as db:
        lead = await db.get(Lead, lead_id)
        if not lead:
            log.error("lead_injection.lead_not_found", lead_id=str(lead_id))
            return

        broker = await db.get(Broker, lead.broker_id)
        if not broker:
            log.error("lead_injection.broker_not_found", broker_id=str(lead.broker_id))
            return

        # Default adapter — instantiated per-call because api_key is per-broker
        if crm is None:
            crm = PropSpaceAdapter(api_key=decrypt(broker.propspace_key_enc))

        messages_result = await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.lead_id == lead_id)
            .order_by(ConversationMessage.sent_at)
        )
        messages = messages_result.scalars().all()
        transcript = _build_transcript(messages)

        score, score_reason = score_lead(
            budget_max=lead.budget_max_aed,
            listing_price_max=broker.listing_price_max,
            timeline_days=lead.timeline_days,
        )

        # Persist score before attempting the push (survives a partial failure)
        lead.score = score
        lead.score_reason = score_reason

        crm_lead = _build_crm_lead(lead, broker, score, score_reason, transcript)

        try:
            crm_id = await crm.push_lead(crm_lead)
            lead.propspace_lead_id = crm_id
            lead.injected_at = func.now()
            lead.status = "INJECTED"
            await db.commit()
            log.info("lead_injection.injected", lead_id=str(lead.id), crm_id=crm_id, score=score)

        except Exception as e:
            log.error("lead_injection.failed", lead_id=str(lead.id), error=str(e))
            lead.status = "INJECT_FAILED"
            await db.commit()
