from typing import Optional, Protocol, runtime_checkable
from pydantic import BaseModel


class ParsedLead(BaseModel):
    """Structured fields extracted from a portal inquiry email."""
    prospect_name: Optional[str] = None
    phone: Optional[str] = None
    property_ref: Optional[str] = None
    portal_source: Optional[str] = None


@runtime_checkable
class IEmailParserPort(Protocol):
    """Abstract contract for extracting lead fields from a raw email."""

    async def parse_lead(
        self, subject: str, text_body: str, html_body: str
    ) -> ParsedLead:
        """
        Parse an inbound portal inquiry email.
        Always returns a ParsedLead — individual fields may be None if not found.
        Must never raise; callers depend on a graceful fallback.
        """
        ...
