"""
Groq email parser adapter — implements IEmailParserPort using Groq's Llama models.

Uses JSON mode for structured output (compatible with all Groq-hosted models).
Swap the default model via GROQ_MODEL_PARSE in your .env.
"""
import json
import structlog
from groq import AsyncGroq

from app.config import settings
from app.ports.email_parser import IEmailParserPort, ParsedLead

log = structlog.get_logger()

_SYSTEM_PROMPT = (
    "You are a UAE real estate lead extraction assistant. "
    "Extract the following fields from the portal inquiry email and return them as a JSON object:\n"
    "- prospect_name: full name of the person making the inquiry (string or null)\n"
    "- phone: their phone number in international format e.g. +971501234567 (string or null)\n"
    "- property_ref: the property reference or listing ID they are asking about (string or null)\n"
    "- portal_source: the real estate portal the inquiry originated from "
    "e.g. Bayut, Property Finder, Dubizzle, Houza (string or null)\n"
    "Return ONLY a JSON object with exactly these four keys. "
    "Use null for any field you cannot confidently extract."
)


class GroqEmailParser:
    """
    Concrete email parser backed by Groq (Llama 3.3 by default).
    Stateless singleton — safe to share across requests.
    Uses JSON mode + manual Pydantic parsing for broad model compatibility.
    Always returns a ParsedLead; never raises (fields will be None on failure).
    """

    def __init__(self) -> None:
        self._client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def parse_lead(self, subject: str, text_body: str, html_body: str) -> ParsedLead:
        content = (text_body or html_body or "").strip()
        if not content and not subject:
            log.warning("email_parser.empty_content")
            return ParsedLead()

        prompt = f"Subject: {subject}\n\nEmail body:\n{content[:4000]}"

        try:
            response = await self._client.chat.completions.create(
                model=settings.GROQ_MODEL_PARSE,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
            raw = response.choices[0].message.content
            data = json.loads(raw)
            # Safely extract only the fields we care about; ignore any extras
            result = ParsedLead(
                prospect_name=data.get("prospect_name"),
                phone=data.get("phone"),
                property_ref=data.get("property_ref"),
                portal_source=data.get("portal_source"),
            )
            log.info(
                "email_parser.extracted",
                provider="groq",
                model=settings.GROQ_MODEL_PARSE,
                name=result.prospect_name,
                phone=result.phone,
                source=result.portal_source,
                property_ref=result.property_ref,
            )
            return result
        except Exception as e:
            log.error("email_parser.failed", provider="groq", error=str(e))
            return ParsedLead()
