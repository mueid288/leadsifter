from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class CRMLead:
    """Value object representing a lead payload to send to any CRM."""
    first_name: str
    last_name: str
    phone: str | None
    source: str
    notes: str
    property_ref: str | None
    tag: str


@runtime_checkable
class ICRMPort(Protocol):
    """Abstract contract for pushing a qualified lead into a CRM."""

    async def push_lead(self, lead: CRMLead) -> str:
        """
        Push a lead to the CRM.
        Returns the CRM-assigned lead ID as a string.
        Raises on unrecoverable failure (after any internal retries).
        """
        ...
