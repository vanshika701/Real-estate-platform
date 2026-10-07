from redis.asyncio import Redis

from app.core.errors import AppError


class LoginRateLimiter:
    """Fixed-window limit on failed logins per email, stored in Redis.

    The window opens on the first failure and lasts `window_seconds`. Keying on the email
    (not IP) protects each account from password guessing even across many IPs.
    """

    def __init__(self, redis: Redis, max_failures: int, window_seconds: int) -> None:
        self.redis = redis
        self.max_failures = max_failures
        self.window_seconds = window_seconds

    @staticmethod
    def _key(email: str) -> str:
        return f"login_fail:{email}"

    async def ensure_allowed(self, email: str) -> None:
        failures = await self.redis.get(self._key(email))
        if failures is None or int(failures) < self.max_failures:
            return
        retry_after = max(await self.redis.ttl(self._key(email)), 1)
        raise AppError(
            "too_many_attempts",
            f"Too many failed login attempts. Try again in {retry_after} seconds.",
            429,
            headers={"Retry-After": str(retry_after)},
        )

    async def record_failure(self, email: str) -> None:
        # INCR + EXPIRE NX in one transaction: the TTL is set only on the first failure,
        # so later failures don't keep pushing the window back.
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.incr(self._key(email))
            pipe.expire(self._key(email), self.window_seconds, nx=True)
            await pipe.execute()

    async def reset(self, email: str) -> None:
        await self.redis.delete(self._key(email))
