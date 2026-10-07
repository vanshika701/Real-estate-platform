from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CurrentUser, DbSession, RedisClient
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(session: DbSession, redis: RedisClient) -> AuthService:
    return AuthService(session, redis)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(data: SignupRequest, service: AuthServiceDep) -> AuthResponse:
    return await service.signup(data)


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, service: AuthServiceDep) -> AuthResponse:
    return await service.login(data)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, service: AuthServiceDep) -> TokenResponse:
    return await service.refresh(data.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)
