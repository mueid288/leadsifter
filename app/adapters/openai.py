import structlog
from openai import AsyncOpenAI

from app.config import settings
from app.ports.email_parser import IEmailParserPort, ParsedLead

log = structlog.get_logger()

_SYSTEM_PROMPT = (
    "You are a UAE real estate lead extraction assistant. "
    "Extract the following fields from the portal inquiry email:\n"
    "- prospect_name: full name of the person making the inquiry\n"
    "- phone: their phone number in international format (e.g. +971501234567)\n"
    "- property_ref: the property reference or listing ID they are asking about\n"
    "- portal_source: the real estate portal the inquiry originated from "
    "(e.g. Bayut, Property Finder, Dubizzle, Houza). "
    "Return null for any field you cannot confidently extract."
)


class OpenAIEmailParser:
    """
    Concrete email parser backed by OpenAI structured output.
    Stateless singleton — safe to share across requests.
    Always returns a ParsedLead; never raises (fields will be None on failure).
    """

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def parse_lead(self, subject: str, text_body: str, html_body: str) -> ParsedLead:
        content = (text_body or html_body or "").strip()
        if not content and not subject:
            log.warning("email_parser.empty_content")
            return ParsedLead()

        prompt = f"Subject: {subject}\n\nEmail body:\n{content[:4000]}"

        try:
            response = await self._client.beta.chat.completions.parse(
                model=settings.OPENAI_MODEL_PARSE,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format=ParsedLead,
            )
            result = response.choices[0].message.parsed
            log.info(
                "email_parser.extracted",
                name=result.prospect_name,
                phone=result.phone,
                source=result.portal_source,
                property_ref=result.property_ref,
            )
            return result
        except Exception as e:
            log.error("email_parser.failed", error=str(e))
            return ParsedLead()
