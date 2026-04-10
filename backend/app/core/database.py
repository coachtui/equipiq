from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# asyncpg requires postgresql+asyncpg:// scheme
_url = settings.database_url
_url = _url.replace("postgresql+asyncpg://", "postgresql://", 1)  # normalise first
_url = _url.replace("postgresql://", "postgresql+asyncpg://", 1)
_url = _url.replace("postgres://", "postgresql+asyncpg://", 1)

engine = create_async_engine(_url, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
