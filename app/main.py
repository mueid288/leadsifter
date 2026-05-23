import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
import structlog

from app.config import settings
from app.routers import email_webhook, whatsapp_webhook, broker, health, internal


def configure_logging() -> None:
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
    ]
    renderer = (
        structlog.dev.ConsoleRenderer()
        if settings.DEBUG
        else structlog.processors.JSONRenderer()
    )
    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


configure_logging()
log = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info('leadsifter.startup')
    yield
    log.info('leadsifter.shutdown')

app = FastAPI(
    title='LeadSifter UAE',
    version='0.1.0',
    lifespan=lifespan,
    docs_url='/docs' if settings.DEBUG else None, 
)

app.include_router(health.router)
app.include_router(email_webhook.router, prefix='/webhook')
app.include_router(whatsapp_webhook.router, prefix='/webhook')
app.include_router(broker.router, prefix='/broker')
app.include_router(internal.router, prefix='/internal', tags=["Internal"])
