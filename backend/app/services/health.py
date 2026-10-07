from typing import Literal

import structlog
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.health import HealthResponse

logger = structlog.get_logger(__name__)

CheckResult = Literal["ok", "error"]


async def _check_database(session: AsyncSession) -> CheckResult:
    # A connectivity probe, not a domain query, so it lives here rather than in a repository.
    try:
        await session.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        logger.exception("health_check_failed", dependency="database")
        return "error"


async def _check_redis(redis: Redis) -> CheckResult:
    try:
        await redis.ping()
        return "ok"
    except Exception:
        logger.exception("health_check_failed", dependency="redis")
        return "error"


async def check_health(session: AsyncSession, redis: Redis) -> HealthResponse:
    database = await _check_database(session)
    redis_status = await _check_redis(redis)
    healthy = database == "ok" and redis_status == "ok"
    return HealthResponse(
        status="ok" if healthy else "degraded",
        checks={"database": database, "redis": redis_status},
    )
