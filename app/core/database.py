from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

async_engine = create_async_engine(settings.DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)
Base = declarative_base()


async def get_db() -> AsyncSession: # type: ignore
    async with AsyncSessionLocal() as session:
        yield session


# Sync — used by Celery workers (swap postgresql+asyncpg → postgresql+psycopg2)
sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg2")
sync_engine = create_engine(sync_url)
SyncSessionLocal = sessionmaker(sync_engine, expire_on_commit=False)