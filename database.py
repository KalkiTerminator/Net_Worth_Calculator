import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Render provides postgresql:// but asyncpg needs postgresql+asyncpg://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL) if DATABASE_URL else None

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False) if engine else None


async def get_db():
    if async_session is None:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    async with async_session() as session:
        yield session
