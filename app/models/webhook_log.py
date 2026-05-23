import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Boolean, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class WebhookLog(Base):
    __tablename__ = "webhook_logs"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    source: Mapped[str] = mapped_column(String)
    method: Mapped[Optional[str]] = mapped_column(String)
    headers: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    body: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    processed: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text("false"))
    error: Mapped[Optional[str]] = mapped_column(String)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=text("NOW()"))

