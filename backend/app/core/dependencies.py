"""Typed dependency aliases so routers declare what they need in one short annotation."""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import AppError
from app.core.redis import get_redis
from app.core.security import TokenType, decode_token
from app.models import User, UserRole
from app.repositories.users import UserRepository

DbSession = Annotated[AsyncSession, Depends(get_session)]
RedisClient = Annotated[Redis, Depends(get_redis)]

# auto_error=False so a missing header goes through our error shape instead of FastAPI's.
_bearer = HTTPBearer(auto_error=False, description="Access token from /auth/login")

_UNAUTHENTICATED_HEADERS = {"WWW-Authenticate": "Bearer"}


async def get_current_user(
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise AppError(
            "not_authenticated", "Authentication required", 401, _UNAUTHENTICATED_HEADERS
        )
    payload = decode_token(credentials.credentials, TokenType.ACCESS)

    # Load the user rather than trusting the token alone, so a deleted account loses access
    # immediately instead of when its token expires.
    user = await UserRepository(session).get_by_id(payload.user_id)
    if user is None:
        raise AppError("invalid_token", "User no longer exists", 401, _UNAUTHENTICATED_HEADERS)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(role: UserRole) -> Callable[[User], Awaitable[User]]:
    async def _check(user: CurrentUser) -> User:
        if user.role is not role:
            raise AppError("forbidden", f"This action requires the {role.value} role", 403)
        return user

    return _check


AgentUser = Annotated[User, Depends(require_role(UserRole.AGENT))]
BuyerUser = Annotated[User, Depends(require_role(UserRole.BUYER))]
