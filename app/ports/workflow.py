import uuid
from typing import Protocol, runtime_checkable


@runtime_checkable
class IWorkflowPort(Protocol):
    """Abstract contract for the external workflow orchestrator (n8n today)."""

    async def trigger_qualification(
        self, broker_id: uuid.UUID, lead_id: uuid.UUID, phone: str
    ) -> None:
        """
        Fire the qualification workflow for a newly received lead.
        Raises on failure so the caller can handle status updates.
        """
        ...

    async def resume_execution(
        self, execution_id: str, body: str, from_number: str
    ) -> None:
        """
        Resume a paused workflow execution with a prospect's reply.
        Logs and swallows errors — a failed resume must not crash the webhook handler.
        """
        ...
