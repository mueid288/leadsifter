from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy import select
import uuid
import structlog

from app.config import settings
from app.database import get_db
from app.models.broker import Broker
from app.crypto import encrypt
from app.schemas.broker import BrokerCreate, BrokerResponse

router = APIRouter()
log = structlog.get_logger()


async def verify_admin_key(x_admin_key: str = Header(...)):
    """Protects broker provisioning — requires X-Admin-Key header."""
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")
    return True


@router.post('/', response_model=BrokerResponse, tags=["Brokers"], dependencies=[Depends(verify_admin_key)])
async def create_or_update_broker(payload: BrokerCreate):
    """
    Creates a new broker, encrypts their BYOK credentials,
    and generates their unique inbound email address.
    Requires X-Admin-Key header.
    """
    async with get_db() as db:
        result = await db.execute(select(Broker).where(Broker.email == payload.email))
        broker = result.scalars().first()

        if not broker:
            safe_agency = "".join(c for c in payload.agency_name if c.isalnum()).lower()
            unique_suffix = uuid.uuid4().hex[:6]
            inbound_email = f"{safe_agency}-{unique_suffix}@inbound.leadsifter.io"

            broker = Broker(
                email=payload.email,
                agency_name=payload.agency_name,
                inbound_email=inbound_email,
                meta_token_enc=encrypt(payload.meta_token),
                meta_phone_id_enc=encrypt(payload.meta_phone_id),
                propspace_key_enc=encrypt(payload.propspace_key),
                listing_price_min=payload.listing_price_min,
                listing_price_max=payload.listing_price_max,
                timezone=payload.timezone,
            )
            db.add(broker)
            log.info("broker.created", email=payload.email, inbound=inbound_email)
        else:
            broker.agency_name = payload.agency_name
            broker.meta_token_enc = encrypt(payload.meta_token)
            broker.meta_phone_id_enc = encrypt(payload.meta_phone_id)
            broker.propspace_key_enc = encrypt(payload.propspace_key)
            broker.listing_price_min = payload.listing_price_min
            broker.listing_price_max = payload.listing_price_max
            log.info("broker.updated", email=payload.email)

        await db.commit()
        await db.refresh(broker)
        return broker
