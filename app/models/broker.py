import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base

class Broker(Base):
    __tablename__ = "brokers"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    email: Mapped[str] = mapped_column(String, unique=True)
    agency_name: Mapped[str] = mapped_column(String)
    inbound_email: Mapped[str] = mapped_column(String, unique=True)
    
    # BYOK credentials (will be encrypted via app-level AES-256)
    meta_token_enc: Mapped[str] = mapped_column(String)
    meta_phone_id_enc: Mapped[str] = mapped_column(String)
    propspace_key_enc: Mapped[str] = mapped_column(String)
    
    # Configuration
    listing_price_min: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("0"))
    listing_price_max: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("0"))
    timezone: Mapped[Optional[str]] = mapped_column(String, server_default=text("'Asia/Dubai'"))
    active: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text("true"))
    plan: Mapped[Optional[str]] = mapped_column(String, server_default=text("'starter'"))
    
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=text("NOW()"))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=text("NOW()"), onupdate=func.now())

