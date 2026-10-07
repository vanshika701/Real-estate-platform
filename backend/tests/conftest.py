import os

# Point at the dedicated test database and Redis DB *before* app modules read settings.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://propvisit:propvisit@localhost:5432/propvisit_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ["APP_ENV"] = "test"

from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal, engine
from app.main import app
from app.models import Base

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


@pytest.fixture(scope="session", autouse=True)
def database_schema() -> Iterator[None]:
    """Build the test schema with the real migrations, so every run also tests them."""
    config = Config(str(ALEMBIC_INI))
    config.attributes["configure_logger"] = False
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
    # Wipe data between tests so each one starts from an empty schema.
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
