from fastapi import APIRouter, Response, status

from app.core.dependencies import DbSession, RedisClient
from app.schemas.health import HealthResponse
from app.services.health import check_health

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse, "description": "A dependency is unreachable"}},
)
async def health(session: DbSession, redis: RedisClient, response: Response) -> HealthResponse:
    result = await check_health(session, redis)
    if result.status != "ok":
        # 503 lets Docker/Render health checks and load balancers react without parsing the body.
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    """Is the process up? Touches neither Postgres nor Redis.

    Platform health checks poll every few seconds; pointing them at /health would spend a
    metered Redis quota on pings, and restarting the API can't fix a database outage anyway.
    """
    return {"status": "ok"}
