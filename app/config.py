from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # Database
    DATABASE_URL: str

    # OpenAI
    OPENAI_API_KEY: str = ''
    OPENAI_MODEL_PARSE: str = 'gpt-4o-mini'
    OPENAI_MODEL_CONVO: str = 'gpt-4o-mini'

    # Groq (alternative AI provider — used when GROQ_API_KEY is set)
    GROQ_API_KEY: str = ''
    GROQ_MODEL_PARSE: str = 'llama-3.3-70b-versatile'

    # External Webhooks & Crypto
    SENDGRID_WEBHOOK_SECRET: str = ''
    META_VERIFY_TOKEN: str
    ENCRYPTION_KEY: str

    # Internal service authentication
    N8N_INTERNAL_KEY: str
    ADMIN_API_KEY: str

    # n8n integration
    N8N_WEBHOOK_BASE: str = 'http://n8n:5678'

    # App
    DEBUG: bool = False
    LOG_LEVEL: str = 'INFO'

settings = Settings()

