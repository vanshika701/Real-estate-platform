import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

import bcrypt
from jose import ExpiredSignatureError, JWTError, jwt

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import UserRole

# bcrypt only looks at the first 72 bytes; bcrypt>=5 raises instead of silently truncating,
# so request schemas must cap password length (enforced in the auth schemas).
BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=get_settings().bcrypt_rounds)
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


@dataclass(frozen=True)
class TokenPayload:
    user_id: int
    role: UserRole
    token_type: TokenType
    jti: str
    expires_at: datetime


def _create_token(user_id: int, role: UserRole, token_type: TokenType, ttl: timedelta) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "role": role.value,
        # The type claim stops a refresh token from being used as an access token and vice versa.
        "type": token_type.value,
        # Unique ID per token, so a used refresh token can be recognised if it's replayed.
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: int, role: UserRole) -> str:
    ttl = timedelta(minutes=get_settings().access_token_expire_minutes)
    return _create_token(user_id, role, TokenType.ACCESS, ttl)


def create_refresh_token(user_id: int, role: UserRole) -> str:
    ttl = timedelta(days=get_settings().refresh_token_expire_days)
    return _create_token(user_id, role, TokenType.REFRESH, ttl)


def decode_token(token: str, expected_type: TokenType) -> TokenPayload:
    settings = get_settings()
    try:
        # Pinning algorithms prevents "alg: none" and algorithm-confusion attacks.
        claims = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except ExpiredSignatureError as exc:
        raise AppError("token_expired", "Token has expired", 401) from exc
    except JWTError as exc:
        raise AppError("invalid_token", "Token is invalid", 401) from exc

    try:
        payload = TokenPayload(
            user_id=int(claims["sub"]),
            role=UserRole(claims["role"]),
            token_type=TokenType(claims["type"]),
            jti=str(claims["jti"]),
            expires_at=datetime.fromtimestamp(claims["exp"], UTC),
        )
    except (KeyError, ValueError) as exc:
        raise AppError("invalid_token", "Token is invalid", 401) from exc

    if payload.token_type is not expected_type:
        raise AppError("invalid_token", f"Expected an {expected_type.value} token", 401)
    return payload
