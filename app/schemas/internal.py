import uuid
from pydantic import BaseModel


class ConversationPayload(BaseModel):
    lead_id: uuid.UUID
    direction: str
    body: str


class LeadStatusPayload(BaseModel):
    status: str


class RegisterQualificationPayload(BaseModel):
    """n8n calls this to register its execution_id before entering a Wait state."""
    phone: str
    lead_id: uuid.UUID
    execution_id: str
