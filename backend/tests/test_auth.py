from datetime import timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import AgentUser, BuyerUser
from app.core.errors import register_error_handlers
from app.core.security import TokenType, _create_token, create_refresh_token
from app.models import UserRole

PASSWORD = "Secret123"


async def signup(
    client: AsyncClient, email: str = "riya@example.com", role: str = "buyer"
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": PASSWORD, "full_name": "Riya S", "role": role},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def login(client: AsyncClient, email: str, password: str = PASSWORD) -> Any:
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --- signup ---------------------------------------------------------------------------------


async def test_signup_returns_user_and_tokens(client: AsyncClient) -> None:
    body = await signup(client, email="Riya@Example.COM", role="agent")

    assert body["user"]["email"] == "riya@example.com"  # normalized
    assert body["user"]["role"] == "agent"
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 15 * 60
    assert body["access_token"] and body["refresh_token"]
    assert "password_hash" not in body["user"]


async def test_signup_rejects_duplicate_email_case_insensitively(client: AsyncClient) -> None:
    await signup(client, email="riya@example.com")

    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "RIYA@example.com",
            "password": PASSWORD,
            "full_name": "Someone Else",
            "role": "buyer",
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("email", "not-an-email"),
        ("password", "short1"),
        ("password", "nodigitshere"),
        ("password", "a1" * 40),  # over bcrypt's 72-byte limit
        ("role", "admin"),
        ("full_name", "   "),
    ],
)
async def test_signup_validates_input(client: AsyncClient, field: str, value: str) -> None:
    payload = {"email": "a@b.com", "password": PASSWORD, "full_name": "A", "role": "buyer"}
    payload[field] = value

    response = await client.post("/api/v1/auth/signup", json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert field in error["message"]


# --- login & /me ----------------------------------------------------------------------------


async def test_login_then_me_returns_current_user(client: AsyncClient) -> None:
    await signup(client)

    response = await login(client, "RIYA@example.com")
    assert response.status_code == 200
    token = response.json()["access_token"]

    me = await client.get("/api/v1/auth/me", headers=bearer(token))
    assert me.status_code == 200
    assert me.json()["email"] == "riya@example.com"


@pytest.mark.parametrize("email", ["riya@example.com", "nobody@example.com"])
async def test_login_failure_is_identical_for_wrong_password_and_unknown_email(
    client: AsyncClient, email: str
) -> None:
    await signup(client)

    response = await login(client, email, "WrongPass1")

    assert response.status_code == 401
    assert response.json() == {
        "error": {"code": "invalid_credentials", "message": "Incorrect email or password"}
    }


async def test_me_requires_a_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"
    assert response.headers["WWW-Authenticate"] == "Bearer"


async def test_me_rejects_garbage_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me", headers=bearer("not.a.jwt"))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


async def test_me_rejects_refresh_token(client: AsyncClient) -> None:
    body = await signup(client)

    response = await client.get("/api/v1/auth/me", headers=bearer(body["refresh_token"]))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


async def test_me_reports_expired_token_distinctly(client: AsyncClient) -> None:
    user_id = (await signup(client))["user"]["id"]
    expired = _create_token(user_id, UserRole.BUYER, TokenType.ACCESS, timedelta(seconds=-1))

    response = await client.get("/api/v1/auth/me", headers=bearer(expired))

    assert response.status_code == 401
    # A distinct code lets the frontend know to refresh instead of logging out.
    assert response.json()["error"]["code"] == "token_expired"


# --- refresh --------------------------------------------------------------------------------


async def test_refresh_issues_new_working_tokens(client: AsyncClient) -> None:
    body = await signup(client)

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]}
    )

    assert response.status_code == 200
    new = response.json()
    assert new["refresh_token"] != body["refresh_token"]
    me = await client.get("/api/v1/auth/me", headers=bearer(new["access_token"]))
    assert me.status_code == 200


async def test_refresh_token_cannot_be_reused(client: AsyncClient) -> None:
    body = await signup(client)
    payload = {"refresh_token": body["refresh_token"]}

    first = await client.post("/api/v1/auth/refresh", json=payload)
    replay = await client.post("/api/v1/auth/refresh", json=payload)

    assert first.status_code == 200
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "invalid_token"


async def test_refresh_rejects_access_token(client: AsyncClient) -> None:
    body = await signup(client)

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": body["access_token"]}
    )

    assert response.status_code == 401


async def test_refresh_rejects_token_for_deleted_user(client: AsyncClient) -> None:
    token = create_refresh_token(999, UserRole.BUYER)

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": token})

    assert response.status_code == 401


# --- role checks ----------------------------------------------------------------------------

role_app = FastAPI()
register_error_handlers(role_app)


@role_app.get("/agent-only")
async def agent_only(user: AgentUser) -> dict[str, int]:
    return {"id": user.id}


@role_app.get("/buyer-only")
async def buyer_only(user: BuyerUser) -> dict[str, int]:
    return {"id": user.id}


@pytest.fixture
async def role_client() -> Any:
    async with AsyncClient(transport=ASGITransport(app=role_app), base_url="http://t") as ac:
        yield ac


@pytest.mark.parametrize(
    ("role", "path", "expected"),
    [
        ("agent", "/agent-only", 200),
        ("buyer", "/agent-only", 403),
        ("buyer", "/buyer-only", 200),
        ("agent", "/buyer-only", 403),
    ],
)
async def test_role_dependencies_enforce_roles(
    client: AsyncClient, role_client: AsyncClient, role: str, path: str, expected: int
) -> None:
    token = (await signup(client, role=role))["access_token"]

    response = await role_client.get(path, headers=bearer(token))

    assert response.status_code == expected
    if expected == 403:
        assert response.json()["error"]["code"] == "forbidden"


# --- rate limiting --------------------------------------------------------------------------


async def test_sixth_attempt_after_five_failures_is_rate_limited(client: AsyncClient) -> None:
    await signup(client)
    for _ in range(5):
        assert (await login(client, "riya@example.com", "WrongPass1")).status_code == 401

    # Blocked even with the correct password: the limit is on attempts, not on guesses.
    response = await login(client, "riya@example.com")

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "too_many_attempts"
    retry_after = int(response.headers["Retry-After"])
    assert 0 < retry_after <= 15 * 60


async def test_successful_login_resets_failure_count(client: AsyncClient) -> None:
    await signup(client)
    for _ in range(4):
        await login(client, "riya@example.com", "WrongPass1")
    assert (await login(client, "riya@example.com")).status_code == 200

    for _ in range(4):
        await login(client, "riya@example.com", "WrongPass1")
    response = await login(client, "riya@example.com")

    assert response.status_code == 200


async def test_rate_limit_is_per_email(client: AsyncClient) -> None:
    await signup(client, email="victim@example.com")
    await signup(client, email="other@example.com")
    for _ in range(5):
        await login(client, "victim@example.com", "WrongPass1")

    response = await login(client, "other@example.com")

    assert response.status_code == 200


async def test_rate_limit_applies_to_unknown_emails(client: AsyncClient) -> None:
    for _ in range(5):
        await login(client, "ghost@example.com", "WrongPass1")

    response = await login(client, "ghost@example.com", "WrongPass1")

    assert response.status_code == 429
