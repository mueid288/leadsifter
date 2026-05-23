import uuid
from pydantic import BaseModel, EmailStr


class BrokerCreate(BaseModel):
    email: EmailStr
    agency_name: str
    meta_token: str
    meta_phone_id: str
    propspace_key: str
    listing_price_min: int = 0
    listing_price_max: int = 0
    timezone: str = "Asia/Dubai"


class BrokerResponse(BaseModel):
    id: uuid.UUID
    email: str
    agency_name: str
    inbound_email: str
    active: bool
