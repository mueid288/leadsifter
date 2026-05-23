import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base

class RawEmail(Base):
    __tablename__ = "raw_emails"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    broker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brokers.id"))
    from_address: Mapped[Optional[str]] = mapped_column(String)
    subject: Mapped[Optional[str]] = mapped_column(String)
    html_body: Mapped[Optional[str]] = mapped_column(String)
    text_body: Mapped[Optional[str]] = mapped_column(String)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=text("NOW()"))
    processed: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text("false"))

class Lead(Base):
    __tablename__ = "leads"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    broker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brokers.id", ondelete="CASCADE"), index=True)
    raw_email_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("raw_emails.id"))
    
    prospect_name: Mapped[Optional[str]] = mapped_column(String)
    phone: Mapped[Optional[str]] = mapped_column(String, index=True)
    property_ref: Mapped[Optional[str]] = mapped_column(String)
    portal_source: Mapped[Optional[str]] = mapped_column(String)
    
    budget_min_aed: Mapped[Optional[int]] = mapped_column(Integer)
    budget_max_aed: Mapped[Optional[int]] = mapped_column(Integer)
    timeline_days: Mapped[Optional[int]] = mapped_column(Integer)
    financing: Mapped[Optional[str]] = mapped_column(String)
    
    score: Mapped[Optional[str]] = mapped_column(String)
    score_reason: Mapped[Optional[str]] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, server_default=text("'RAW'"), index=True)
    status_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=text("NOW()"), onupdate=func.now())

    propspace_lead_id: Mapped[Optional[str]] = mapped_column(String)
    injected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=text("NOW()"))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=text("NOW()"), onupdate=func.now())

