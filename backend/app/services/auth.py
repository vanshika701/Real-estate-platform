import asyncio
from datetime import UTC, datetime
from functools import cache

import structlog
from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import User
from app.repositories.users import UserRepository
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from app.services.login_rate_limiter import LoginRateLimiter

logger = structlog.get_logger(__name__)

INVALID_CREDENTIALS = AppError("invalid_credentials", "Incorrect email or password", 401)


@cache
def _dummy_hash() -> str:
    return hash_password("timing-equalizer-not-a-real-password")


class AuthService:
    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        settings = get_settings()
        self.session = session
        self.redis = redis
        self.users = UserRepository(session)
        self.rate_limiter = LoginRateLimiter(
            redis, settings.login_max_failed_attempts, settings.login_lockout_seconds
        )

    async def signup(self, data: SignupRequest) -> AuthResponse:
        if await self.users.get_by_email(data.email) is not None:
            raise AppError("email_taken", "An account with this email already exists", 409)

        # bcrypt is CPU-bound (~250 ms); running it in a thread keeps the event loop serving
        # other requests meanwhile.
        password_hash = await asyncio.to_thread(hash_password, data.password)
        try:
            user = await self.users.create(
                email=data.email,
                password_hash=password_hash,
                full_name=data.full_name,
                role=data.role,
                phone=data.phone,
            )
            await self.session.commit()
        except IntegrityError as exc:
            # Two concurrent signups with the same email: the unique constraint decides.
            await self.session.rollback()
            raise AppError("email_taken", "An account with this email already exists", 409) from exc

        logger.info("user_signed_up", user_id=user.id, role=user.role.value)
        return self._auth_response(user)

    async def login(self, data: LoginRequest) -> AuthResponse:
        await self.rate_limiter.ensure_allowed(data.email)

        user = await self.users.get_by_email(data.email)
        # Always run bcrypt, even for unknown emails, so response time doesn't reveal
        # which emails are registered.
        password_hash = user.password_hash if user else _dummy_hash()
        password_ok = await asyncio.to_thread(verify_password, data.password, password_hash)

        if user is None or not password_ok:
            await self.rate_limiter.record_failure(data.email)
            logger.info("login_failed", known_user=user is not None)
            raise INVALID_CREDENTIALS

        await self.rate_limiter.reset(data.email)
        logger.info("login_succeeded", user_id=user.id)
        return self._auth_response(user)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token, TokenType.REFRESH)

        # Rotation: each refresh token works once. SET NX on its ID is atomic, so if a stolen
        # token is replayed after the real client used it (or vice versa), the second use fails.
        # The key only needs to live as long as the token itself would.
        ttl = max(int((payload.expires_at - datetime.now(UTC)).total_seconds()), 1)
        first_use = await self.redis.set(f"refresh_used:{payload.jti}", "1", nx=True, ex=ttl)
        if not first_use:
            logger.warning("refresh_token_reused", user_id=payload.user_id)
            raise AppError("invalid_token", "Refresh token has already been used", 401)

        user = await self.users.get_by_id(payload.user_id)
        if user is None:
            raise AppError("invalid_token", "User no longer exists", 401)
        return self._tokens(user)

    @staticmethod
    def _tokens(user: User) -> TokenResponse:
        return TokenResponse(
            access_token=create_access_token(user.id, user.role),
            refresh_token=create_refresh_token(user.id, user.role),
            expires_in=get_settings().access_token_expire_minutes * 60,
        )

    def _auth_response(self, user: User) -> AuthResponse:
        tokens = self._tokens(user)
        return AuthResponse(**tokens.model_dump(), user=UserResponse.model_validate(user))
