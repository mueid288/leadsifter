from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

@asynccontextmanager
async def get_db():
    """Context manager for use in services and background tasks."""
    async with SessionLocal() as session:
        yield session

async def get_db_dep() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends()-compatible dependency."""
    async with SessionLocal() as session:
        yield session
