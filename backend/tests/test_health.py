from httpx import AsyncClient
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.redis import get_redis
from app.main import app


class _UnreachableRedis:
    async def ping(self) -> bool:
        raise RedisConnectionError("connection refused")


async def test_health_ok_when_dependencies_are_up(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok", "redis": "ok"}}


async def test_health_returns_503_when_redis_is_down(client: AsyncClient) -> None:
    app.dependency_overrides[get_redis] = lambda: _UnreachableRedis()

    response = await client.get("/api/v1/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"] == {"database": "ok", "redis": "error"}


async def test_liveness_does_not_touch_dependencies(client: AsyncClient) -> None:
    # Redis being down must not fail liveness: that's /health's job.
    app.dependency_overrides[get_redis] = lambda: _UnreachableRedis()

    response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_unknown_route_uses_error_shape(client: AsyncClient) -> None:
    response = await client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Not Found"}}


async def test_responses_carry_request_id(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health", headers={"X-Request-ID": "abc123"})

    assert response.headers["X-Request-ID"] == "abc123"
