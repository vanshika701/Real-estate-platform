import os

# Point at the dedicated test database and Redis DB *before* app modules read settings.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://propvisit:propvisit@localhost:5432/propvisit_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ["APP_ENV"] = "test"

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
