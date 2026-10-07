import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import BCRYPT_MAX_BYTES
from app.models import UserRole


def _normalize_email(value: str) -> str:
    # EmailStr only lowercases the domain; we treat the whole address case-insensitively.
    return value.strip().lower()


NormalizedEmail = Annotated[EmailStr, AfterValidator(_normalize_email)]


class SignupRequest(BaseModel):
    email: NormalizedEmail
    password: str = Field(min_length=8, max_length=BCRYPT_MAX_BYTES)
    full_name: str = Field(min_length=1, max_length=120)
    role: UserRole
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9]{10,15}$")

    @field_validator("full_name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("password")
    @classmethod
    def _password_strength(cls, value: str) -> str:
        if len(value.encode()) > BCRYPT_MAX_BYTES:
            raise ValueError(f"must be at most {BCRYPT_MAX_BYTES} bytes")
        if not (re.search(r"[A-Za-z]", value) and re.search(r"\d", value)):
            raise ValueError("must contain at least one letter and one number")
        return value


class LoginRequest(BaseModel):
    email: NormalizedEmail
    # No strength rules here: those apply when a password is chosen, not when it's checked.
    password: str = Field(min_length=1, max_length=BCRYPT_MAX_BYTES)


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    phone: str | None
    role: UserRole
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - OAuth2 token type, not a secret
    expires_in: int = Field(description="Access token lifetime in seconds")


class AuthResponse(TokenResponse):
    """Signup and login also return the user, saving the client a follow-up /auth/me call."""

    user: UserResponse
