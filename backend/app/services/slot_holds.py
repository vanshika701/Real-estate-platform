from dataclasses import dataclass
from datetime import datetime

from redis.asyncio import Redis

# Delete the key only if it still belongs to this buyer. GET-then-DEL from Python would race:
# the hold could expire and be taken by someone else between the two calls, and we'd delete
# their hold. A Lua script runs atomically inside Redis.
_RELEASE_IF_OWNER = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""


@dataclass(frozen=True)
class HoldResult:
    acquired: bool
    holder_id: int | None
    ttl_seconds: int


class SlotHoldStore:
    """Short-lived exclusive claims on a slot while a buyer confirms their booking."""

    def __init__(self, redis: Redis, ttl_seconds: int) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds
        self._release_script = redis.register_script(_RELEASE_IF_OWNER)

    @staticmethod
    def key(listing_id: int, slot_start: datetime) -> str:
        # Unix seconds, not an ISO string: the same instant written with a different timezone
        # offset must map to the same key.
        return f"hold:{listing_id}:{int(slot_start.timestamp())}"

    async def acquire(self, listing_id: int, slot_start: datetime, buyer_id: int) -> HoldResult:
        key = self.key(listing_id, slot_start)
        # Two attempts: if the other hold expires between our SET and GET, try once more.
        for _ in range(2):
            if await self.redis.set(key, str(buyer_id), nx=True, ex=self.ttl_seconds):
                return HoldResult(acquired=True, holder_id=buyer_id, ttl_seconds=self.ttl_seconds)

            # Someone holds it. If it's this buyer (e.g. a double click), report their existing
            # hold without extending it, so a hold can't be renewed forever.
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.get(key)
                pipe.ttl(key)
                holder, ttl = await pipe.execute()
            if holder is not None:
                holder_id = int(holder)
                return HoldResult(
                    acquired=holder_id == buyer_id, holder_id=holder_id, ttl_seconds=max(ttl, 0)
                )
        return HoldResult(acquired=False, holder_id=None, ttl_seconds=0)

    async def holder(self, listing_id: int, slot_start: datetime) -> int | None:
        value = await self.redis.get(self.key(listing_id, slot_start))
        return int(value) if value is not None else None

    async def held_slots(self, listing_id: int, slot_starts: list[datetime]) -> set[datetime]:
        """Which of these slots are currently held. One MGET round trip for the whole list."""
        if not slot_starts:
            return set()
        values = await self.redis.mget([self.key(listing_id, s) for s in slot_starts])
        return {start for start, value in zip(slot_starts, values, strict=True) if value}

    async def release(self, listing_id: int, slot_start: datetime, buyer_id: int) -> bool:
        deleted = await self._release_script(
            keys=[self.key(listing_id, slot_start)], args=[str(buyer_id)]
        )
        return bool(deleted)
