"""
Application container — singleton adapter instances.

Stateless adapters (OpenAI, n8n) are safe to share across all requests.

PropSpaceAdapter is intentionally NOT a singleton: it must be instantiated
per-call with the broker's decrypted API key, which is fetched from the DB
at injection time inside `services/lead_injection.py`.
"""
from app.adapters.openai import OpenAIEmailParser
from app.adapters.n8n import N8NWorkflowAdapter

email_parser: OpenAIEmailParser = OpenAIEmailParser()
workflow: N8NWorkflowAdapter = N8NWorkflowAdapter()
