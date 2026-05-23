import uuid
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

from app.config import settings
from app.ports.crm import ICRMPort, CRMLead

log = structlog.get_logger()

_PROPSPACE_BASE = 'https://api.propspace.com/v1'


class PropSpaceAdapter:
    """
    Concrete CRM adapter for PropSpace.
    Instantiated per-call with the broker's decrypted API key.
    Retries up to 3 times with exponential backoff on HTTP failure.
    In DEBUG mode, returns a mock ID without making any HTTP call.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=30),
        reraise=True,
    )
    async def push_lead(self, lead: CRMLead) -> str:
        if settings.DEBUG:
            mock_id = f"mock_propspace_{uuid.uuid4().hex[:6]}"
            log.info('propspace.mock_push', phone=lead.phone, mock_id=mock_id)
            return mock_id

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f'{_PROPSPACE_BASE}/leads',
                json={
                    'firstName': lead.first_name,
                    'lastName': lead.last_name,
                    'phone': lead.phone,
                    'source': lead.source,
                    'notes': lead.notes,
                    'propertyRef': lead.property_ref,
                    'tag': lead.tag,
                },
                headers={
                    'Authorization': f'Bearer {self._api_key}',
                    'Content-Type': 'application/json',
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return str(data.get('id', ''))
