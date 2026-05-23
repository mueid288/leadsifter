from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import text
import structlog

from app.database import get_db

router = APIRouter()
log = structlog.get_logger()


@router.get("/health", tags=["System"])
async def health_check():
    """Returns healthy only when the database is reachable."""
    try:
        async with get_db() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "healthy", "version": "0.1.0"}
    except Exception as e:
        log.error("health.db_check_failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": "Database unreachable"},
        )
