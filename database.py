# database.py — Sets up the connection to our PostgreSQL database.
#
# KEY CONCEPTS:
# - We use SQLAlchemy as an ORM (Object-Relational Mapper). An ORM lets us
#   interact with the database using Python objects instead of writing raw SQL.
# - "async" means non-blocking — the server can handle other requests while
#   waiting for the database to respond. This makes our app faster.
# - The DATABASE_URL is stored as an "environment variable" on Render (not in
#   code) so that our database credentials stay secret and out of GitHub.

import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Read the database connection URL from the environment.
# On Render, this is set in the Environment tab of your web service.
# Locally, it would be empty ("") unless you set it yourself.
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Render gives us a URL like: postgresql://user:pass@host:5432/dbname
# But our async driver (asyncpg) needs: postgresql+asyncpg://user:pass@host:5432/dbname
# So we replace the prefix to make it compatible.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# The "engine" is SQLAlchemy's connection manager — it handles the actual
# connection pool to our PostgreSQL database. Think of it as the "bridge"
# between our Python code and the database.
engine = create_async_engine(DATABASE_URL) if DATABASE_URL else None

# A "session" is like a conversation with the database. Each request to our
# app gets its own session. async_sessionmaker is a factory that creates
# these sessions on demand.
# expire_on_commit=False means we can still read data from objects after
# committing (saving) them, without making another database query.
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False) if engine else None


async def get_db():
    """
    FastAPI "dependency" that provides a database session to our route functions.

    HOW IT WORKS:
    - FastAPI calls this function automatically when a route needs a "db" parameter.
    - It creates a new database session, gives it to the route, and then
      automatically closes it when the route is done.
    - The "yield" keyword makes this a generator — everything before yield runs
      before the route, and everything after yield runs as cleanup.
    """
    if async_session is None:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    async with async_session() as session:
        yield session
