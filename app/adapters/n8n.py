import uuid
import httpx
import structlog

from app.config import settings
from app.ports.workflow import IWorkflowPort

log = structlog.get_logger()


class N8NWorkflowAdapter:
    """
    Concrete workflow adapter that communicates with n8n via its webhook endpoints.
    Stateless singleton — safe to share across requests.
    """

    async def trigger_qualification(
        self, broker_id: uuid.UUID, lead_id: uuid.UUID, phone: str
    ) -> None:
        """POST to the n8n start-qualification webhook. Raises on failure."""
        url = f"{settings.N8N_WEBHOOK_BASE}/webhook/start-qualification"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json={
                "broker_id": str(broker_id),
                "lead_id": str(lead_id),
                "phone": phone,
            })
            resp.raise_for_status()
        log.info("workflow.qualification_triggered", lead_id=str(lead_id), phone=phone)

    async def resume_execution(
        self, execution_id: str, body: str, from_number: str
    ) -> None:
        """POST to the n8n webhook-waiting endpoint to resume a paused execution. Logs on failure."""
        url = f"{settings.N8N_WEBHOOK_BASE}/webhook-waiting/{execution_id}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(url, json={"body": body, "from": from_number})
            log.info("workflow.execution_resumed", execution_id=execution_id, phone=from_number)
        except Exception as e:
            log.error("workflow.resume_failed", execution_id=execution_id, error=str(e))
