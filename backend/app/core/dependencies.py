"""Typed dependency aliases so routers declare what they need in one short annotation."""

from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.redis import get_redis

DbSession = Annotated[AsyncSession, Depends(get_session)]
RedisClient = Annotated[Redis, Depends(get_redis)]
