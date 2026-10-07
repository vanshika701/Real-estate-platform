from functools import cache

from redis import Redis as SyncRedis
from redis.asyncio import Redis

from app.core.config import get_settings

# from_url does not open a connection; the pool connects lazily on first command.
redis_client: Redis = Redis.from_url(get_settings().redis_url, decode_responses=True)


async def get_redis() -> Redis:
    return redis_client


@cache
def get_sync_redis() -> SyncRedis:
    """Blocking client for RQ, which doesn't support asyncio. RQ stores pickled bytes, so
    responses must not be decoded."""
    return SyncRedis.from_url(get_settings().redis_url)
