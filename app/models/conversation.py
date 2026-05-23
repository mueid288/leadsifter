import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    direction: Mapped[str] = mapped_column(String)
    wa_message_id: Mapped[Optional[str]] = mapped_column(String, index=True) 
    body: Mapped[str] = mapped_column(String)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=text("NOW()"))

class ActiveQualification(Base):
    __tablename__ = "active_qualifications"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    phone: Mapped[str] = mapped_column(String, index=True, unique=True)
    execution_id: Mapped[str] = mapped_column(String)
    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"))
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=text("NOW()"))


