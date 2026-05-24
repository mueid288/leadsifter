# LeadSifter

An automated lead qualification SaaS for UAE real estate brokers. LeadSifter receives inbound portal inquiries via email (SendGrid), qualifies prospects over WhatsApp using an AI-driven conversation loop (n8n + OpenAI), and injects fully-qualified leads into PropSpace CRM.

---

## How It Works

```
Portal Email (Bayut / PF / Dubizzle)
        │
        ▼
SendGrid Inbound Parse
        │
        ▼
POST /webhook/email  ──► OpenAI extracts (name, phone, property, source)
        │
        ▼
Lead created in DB ──► n8n qualification workflow triggered
        │
        ▼
WhatsApp messages sent to prospect (Meta Cloud API)
        │  (prospect replies loop back via POST /webhook/whatsapp)
        ▼
OpenAI extracts (budget, timeline, financing)
        │
        ├── Not qualified ──► Lead marked COLD
        │
        └── Qualified ──► PropSpace CRM injection ──► Lead marked INJECTED
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| Database | PostgreSQL 16 (asyncpg + SQLAlchemy 2.0 async) |
| Migrations | Alembic |
| Workflow orchestration | n8n (self-hosted) |
| AI parsing | OpenAI (`gpt-4o-mini`, structured output) |
| Messaging | Meta WhatsApp Cloud API |
| CRM | PropSpace |
| Email ingestion | SendGrid Inbound Parse |
| Encryption | Fernet (AES-128-CBC) for BYOK credentials |
| Logging | structlog (JSON in prod, ConsoleRenderer in debug) |
| Package manager | uv |
| Containerisation | Docker + Docker Compose |

---

## Project Structure

```
app/
├── ports/               # Abstract interfaces (Protocols)
│   ├── crm.py           # ICRMPort, CRMLead
│   ├── email_parser.py  # IEmailParserPort, ParsedLead
│   └── workflow.py      # IWorkflowPort
├── adapters/            # Concrete third-party implementations
│   ├── propspace.py     # PropSpaceAdapter  → ICRMPort
│   ├── openai.py        # OpenAIEmailParser → IEmailParserPort
│   └── n8n.py           # N8NWorkflowAdapter → IWorkflowPort
├── services/            # Orchestration layer (zero third-party imports)
│   ├── lead_injection.py
│   ├── whatsapp.py
│   └── lead_scorer.py
├── routers/             # FastAPI route handlers
│   ├── email_webhook.py
│   ├── whatsapp_webhook.py
│   ├── broker.py
│   ├── internal.py
│   └── health.py
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic request/response schemas
├── container.py         # Singleton adapter instances
├── config.py            # Pydantic settings (reads from .env)
├── crypto.py            # Fernet encrypt/decrypt helpers
└── database.py          # Async engine + session factory

n8n/
└── leadsifter_qualification_workflow.json   # Import this into n8n

alembic/
└── versions/            # Database migration scripts
```

---

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | — | DB connectivity check |
| `POST` | `/webhook/email` | — | SendGrid Inbound Parse receiver |
| `GET` | `/webhook/whatsapp` | — | Meta webhook verification |
| `POST` | `/webhook/whatsapp` | — | Inbound WhatsApp message handler |
| `POST` | `/broker/` | `X-Admin-Key` | Create / update a broker |
| `GET` | `/internal/broker/{id}` | `X-Internal-Key` | Fetch decrypted broker credentials (n8n) |
| `POST` | `/internal/qualification` | `X-Internal-Key` | Register n8n execution_id before Wait node |
| `POST` | `/internal/conversation` | `X-Internal-Key` | Log an outbound WhatsApp message |
| `PATCH` | `/internal/lead/{id}/status` | `X-Internal-Key` | Update lead status (COLD / QUALIFIED) |

Interactive docs available at `/docs` when `DEBUG=true`.

---

## Local Development

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (`pip install uv`)
- Docker + Docker Compose

### 1. Clone and install

```bash
git clone https://github.com/mueid288/leadsifter.git
cd leadsifter
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in all values — see comments in .env.example
```

The minimum required values for local dev:

```env
DATABASE_URL=postgresql+asyncpg://leadsifter:leadsifter_dev@localhost:5432/leadsifter
OPENAI_API_KEY=sk-...
META_VERIFY_TOKEN=any_string
ENCRYPTION_KEY=  # generate below
N8N_INTERNAL_KEY=any_strong_secret
ADMIN_API_KEY=any_strong_secret
DEBUG=true
```

Generate a Fernet encryption key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. Start dependencies

```bash
docker compose up postgres n8n
```

### 4. Run migrations

```bash
uv run alembic upgrade head
```

### 5. Start the API

```bash
uv run uvicorn app.main:app --reload
# or: python main.py
```

The API is now running at `http://localhost:8000`.

---

## Running the Full Stack

```bash
docker compose up
```

This starts PostgreSQL, n8n, and the LeadSifter API together. The API overrides `DATABASE_URL` and `N8N_WEBHOOK_BASE` to use container hostnames automatically.

> **Note:** Add `N8N_INTERNAL_KEY` to the `n8n` service environment in `docker-compose.yml` so the workflow can reference it via `$env.N8N_INTERNAL_KEY`.

---

## n8n Workflow Setup

1. Open n8n at `http://localhost:5678`
2. Go to **Workflows → Import**
3. Import `n8n/leadsifter_qualification_workflow.json`
4. Set `N8N_INTERNAL_KEY` as an n8n environment variable (Settings → Environment Variables)
5. Configure the **OpenAI** credential in n8n
6. Create the `lead_qualification_start` WhatsApp message template in Meta Business Manager
7. Activate the workflow

---

## Local Testing & WhatsApp Sandbox

For local development and testing, LeadSifter includes a **Zero-Dependency Mock WhatsApp API & Sandbox UI**. This allows you to simulate the entire WhatsApp qualification loop interactively in your browser without connecting a real WhatsApp account or making requests to Meta's servers.

### 1. Enable Sandbox
Ensure your `.env` has `DEBUG=true` enabled:
```env
DEBUG=true
```

### 2. Access the Chat Sandbox
Open your browser and navigate to:
`http://localhost:8000/mock/whatsapp/sandbox`

### 3. Verification & Usage Flow
1. **Inject a mock lead**: Send a simulated email webhook request:
   ```bash
   curl -X POST http://localhost:8000/webhook/email \
     -F "to=testagency-1faf4b@inbound.leadsifter.io" \
     -F "from=buyer@gmail.com" \
     -F "subject=Inquiry about property BAY-001" \
     -F "text=Hi, I'm Ahmed. My number is +971501234567. Interested in BAY-001."
   ```
2. **Interact**: Select the lead in the Sandbox UI. You will see the welcome template message.
3. **Simulate Prospect**: Type a message (or click one of the quick preset buttons) and click **Simulate Reply**. The n8n workflow will process the message and the bot's next question will automatically appear in the chat history!

---

## Broker Provisioning

Create a broker via the admin API:

```bash
curl -X POST http://localhost:8000/broker/ \
  -H "X-Admin-Key: your_admin_key" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "agent@realty.ae",
    "agency_name": "Realty Dubai",
    "meta_token": "EAAxxxx",
    "meta_phone_id": "1234567890",
    "propspace_key": "ps_live_xxxx",
    "listing_price_min": 500000,
    "listing_price_max": 3000000,
    "timezone": "Asia/Dubai"
  }'
```

The response includes the broker's unique `inbound_email` address — configure SendGrid to forward portal emails to this address.

---

## Lead Scoring

Leads are scored automatically at CRM injection time:

| Score | Condition |
|---|---|
| `HOT` | Budget ≥ 85% of listing price **and** timeline ≤ 60 days |
| `WARM` | Budget ≥ 70% of listing price **or** timeline ≤ 120 days |
| `COLD` | Budget < 70% of listing price |

---

## Architecture: Ports & Adapters

Third-party integrations are isolated behind Protocol interfaces. The service layer has **zero** direct imports of `httpx`, `openai`, or `tenacity`.

To swap PropSpace for a different CRM, implement `ICRMPort` and pass it to `inject_lead()`:

```python
from app.ports.crm import ICRMPort, CRMLead

class MyCRMAdapter:
    async def push_lead(self, lead: CRMLead) -> str:
        ...  # your implementation
```

The same pattern applies to `IEmailParserPort` (swap the AI model) and `IWorkflowPort` (swap the workflow engine).

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | ✅ | — | PostgreSQL async URL |
| `OPENAI_API_KEY` | ✅ | — | OpenAI API key |
| `OPENAI_MODEL_PARSE` | | `gpt-4o-mini` | Model used for email parsing |
| `OPENAI_MODEL_CONVO` | | `gpt-4o-mini` | Model used for conversation (n8n) |
| `META_VERIFY_TOKEN` | ✅ | — | Meta webhook verification token |
| `ENCRYPTION_KEY` | ✅ | — | Fernet key for BYOK credential encryption |
| `N8N_INTERNAL_KEY` | ✅ | — | Shared secret between FastAPI and n8n |
| `ADMIN_API_KEY` | ✅ | — | Key for broker provisioning endpoint |
| `N8N_WEBHOOK_BASE` | | `http://n8n:5678` | Base URL of the n8n instance |
| `SENDGRID_WEBHOOK_SECRET` | | `""` | SendGrid webhook signature key (optional) |
| `DEBUG` | | `false` | Enables `/docs`, ConsoleRenderer logging, mock CRM |
| `LOG_LEVEL` | | `INFO` | Logging level |

---

## License

MIT
