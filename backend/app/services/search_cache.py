import hashlib
import json

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.schemas.listings import ListingFilters, ListingPage

logger = structlog.get_logger(__name__)

KEY_PREFIX = "search:"
KEY_SET = "search:keys"


class SearchCache:
    """Caches GET /listings pages in Redis.

    Every cached key is also recorded in a set, so a listing change can drop all cached
    searches at once: any result page might include the listing that changed.

    Redis failures are logged and treated as cache misses. The cache is an optimisation,
    so a Redis outage should make search slower, not broken.
    """

    def __init__(self, redis: Redis, enabled: bool, ttl_seconds: int) -> None:
        self.redis = redis
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def key_for(filters: ListingFilters) -> str:
        canonical = json.dumps(filters.cache_identity(), sort_keys=True, separators=(",", ":"))
        return KEY_PREFIX + hashlib.sha256(canonical.encode()).hexdigest()

    async def get(self, filters: ListingFilters) -> ListingPage | None:
        if not self.enabled:
            return None
        try:
            raw = await self.redis.get(self.key_for(filters))
        except RedisError:
            logger.warning("search_cache_unavailable", op="get", exc_info=True)
            return None
        return ListingPage.model_validate_json(raw) if raw else None

    async def set(self, filters: ListingFilters, page: ListingPage) -> None:
        if not self.enabled:
            return
        key = self.key_for(filters)
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.set(key, page.model_dump_json(), ex=self.ttl_seconds)
                pipe.sadd(KEY_SET, key)
                # The set expires with its newest member, so it can't grow without bound
                # from entries that have already expired.
                pipe.expire(KEY_SET, self.ttl_seconds)
                await pipe.execute()
        except RedisError:
            logger.warning("search_cache_unavailable", op="set", exc_info=True)

    async def invalidate_all(self) -> None:
        # Runs even when caching is disabled, so flipping the flag never leaves stale entries.
        try:
            keys = await self.redis.smembers(KEY_SET)
            await self.redis.delete(KEY_SET, *keys)
        except RedisError:
            # Entries still expire after their TTL, so the worst case is briefly stale results.
            logger.warning("search_cache_unavailable", op="invalidate", exc_info=True)
