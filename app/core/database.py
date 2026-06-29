from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase,Session, sessionmaker

from .config import settings

async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, expire_on_commit=False, autoflush=False, autocommit=False
)
class Base (DeclarativeBase):
    pass


# Sync — used by Celery workers (swap postgresql+asyncpg → postgresql+psycopg2)
sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
sync_engine = create_engine(sync_url)
SyncSessionLocal = sessionmaker(
    expire_on_commit=False, bind=sync_engine, autoflush=False, autocommit=False
)

async def get_db() -> AsyncSession:  # type: ignore
    async with AsyncSessionLocal() as session:
        try:
          yield session
        finally:
            await session.close()  


def get_sync_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()
