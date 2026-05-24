"""
Application container — singleton adapter instances.

Stateless adapters (email parser, n8n) are safe to share across all requests.

The email parser is auto-selected based on which API key is configured:
  - GROQ_API_KEY set   → GroqEmailParser  (Llama 3.3)
  - OPENAI_API_KEY set → OpenAIEmailParser (GPT-4o-mini)

PropSpaceAdapter is intentionally NOT a singleton: it must be instantiated
per-call with the broker's decrypted API key, which is fetched from the DB
at injection time inside `services/lead_injection.py`.
"""
from app.config import settings
from app.adapters.n8n import N8NWorkflowAdapter
from app.ports.email_parser import IEmailParserPort


def _build_email_parser() -> IEmailParserPort:
    """Pick the email parser based on whichever API key is configured."""
    if settings.GROQ_API_KEY:
        from app.adapters.groq import GroqEmailParser
        return GroqEmailParser()
    if settings.OPENAI_API_KEY:
        from app.adapters.openai import OpenAIEmailParser
        return OpenAIEmailParser()
    raise RuntimeError(
        "No AI provider configured. Set GROQ_API_KEY or OPENAI_API_KEY in your .env."
    )


email_parser: IEmailParserPort = _build_email_parser()
workflow: N8NWorkflowAdapter = N8NWorkflowAdapter()
