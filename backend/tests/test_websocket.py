import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pytest
from httpx import AsyncClient
from httpx_ws import AsyncWebSocketSession, WebSocketDisconnect, aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_client
from app.core.security import create_access_token, create_refresh_token
from app.main import app
from app.models import Listing, User, UserRole
from app.services.agent_events import CLOSE_FORBIDDEN, CLOSE_UNAUTHORIZED, agent_channel
from tests.factories import auth_headers, future_slot_start, make_listing, make_slot, make_user

WS_URL = "http://test/api/v1/ws/agent"


@dataclass
class World:
    agent: User
    buyer: User
    listing: Listing
    slot_start: datetime


@pytest.fixture
async def world(db_session: AsyncSession) -> World:
    agent = await make_user(db_session, UserRole.AGENT)
    buyer = await make_user(db_session, UserRole.BUYER)
    listing = await make_listing(db_session, agent)
    start = future_slot_start()
    await make_slot(db_session, listing, start)
    return World(agent, buyer, listing, start)


@asynccontextmanager
async def connect(token: str | None) -> AsyncIterator[AsyncWebSocketSession]:
    # Opened inside the test (not a fixture): the transport's task group must be entered and
    # exited by the same task.
    url = WS_URL if token is None else f"{WS_URL}?token={token}"
    async with (
        AsyncClient(transport=ASGIWebSocketTransport(app)) as client,
        aconnect_ws(url, client) as ws,
    ):
        yield ws


def _leaves(exc: BaseException) -> list[BaseException]:
    if isinstance(exc, BaseExceptionGroup):
        return [leaf for inner in exc.exceptions for leaf in _leaves(inner)]
    return [exc]


async def close_code(token: str | None) -> int | None:
    disconnects: list[WebSocketDisconnect] = []
    try:
        async with connect(token) as ws:
            await ws.receive_text(timeout=2)
    except* WebSocketDisconnect as group:  # the transport wraps it in (nested) ExceptionGroups
        disconnects = [e for e in _leaves(group) if isinstance(e, WebSocketDisconnect)]
    return disconnects[0].code if disconnects else None


def token_for(user: User) -> str:
    return create_access_token(user.id, user.role)


async def subscriber_count(agent_id: int) -> int:
    counts = await redis_client.pubsub_numsub(agent_channel(agent_id))
    return int(counts[0][1]) if counts else 0


async def wait_for_subscribers(agent_id: int, expected: int) -> None:
    """The socket subscribes after the handshake; publishing before that would be lost."""
    for _ in range(200):
        if await subscriber_count(agent_id) == expected:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"expected {expected} subscribers on agent {agent_id}'s channel")


async def book(client: AsyncClient, w: World) -> dict[str, Any]:
    await client.post(
        f"/api/v1/listings/{w.listing.id}/slots/hold",
        json={"slot_start": w.slot_start.isoformat()},
        headers=auth_headers(w.buyer),
    )
    response = await client.post(
        "/api/v1/bookings",
        json={"listing_id": w.listing.id, "slot_start": w.slot_start.isoformat()},
        headers=auth_headers(w.buyer),
    )
    assert response.status_code == 201
    return response.json()


async def test_agent_receives_booking_created_and_cancelled(
    client: AsyncClient, world: World
) -> None:
    async with connect(token_for(world.agent)) as ws:
        await wait_for_subscribers(world.agent.id, 1)

        booking = await book(client, world)
        created = await ws.receive_json(timeout=3)

        await client.patch(
            f"/api/v1/bookings/{booking['id']}/cancel", headers=auth_headers(world.buyer)
        )
        cancelled = await ws.receive_json(timeout=3)

    assert created["type"] == "booking.created"
    assert created["booking"]["id"] == booking["id"]
    assert created["booking"]["buyer"]["email"] == world.buyer.email
    assert created["booking"]["status"] == "pending"
    assert cancelled["type"] == "booking.cancelled"
    assert cancelled["booking"]["status"] == "cancelled"


async def test_agent_only_receives_events_for_own_listings(
    client: AsyncClient, world: World, db_session: AsyncSession
) -> None:
    other_agent = await make_user(db_session, UserRole.AGENT)

    async with connect(token_for(other_agent)) as ws:
        await wait_for_subscribers(other_agent.id, 1)
        await book(client, world)

        with pytest.raises(TimeoutError):
            await ws.receive_json(timeout=1.5)


@pytest.mark.parametrize(
    ("token_kind", "expected"),
    [
        ("missing", CLOSE_UNAUTHORIZED),
        ("garbage", CLOSE_UNAUTHORIZED),
        ("refresh", CLOSE_UNAUTHORIZED),
        ("buyer", CLOSE_FORBIDDEN),
    ],
)
async def test_socket_rejects_bad_credentials(world: World, token_kind: str, expected: int) -> None:
    token = {
        "missing": None,
        "garbage": "not-a-jwt",
        "refresh": create_refresh_token(world.agent.id, world.agent.role),
        "buyer": token_for(world.buyer),
    }[token_kind]

    assert await close_code(token) == expected


async def test_socket_unsubscribes_on_disconnect(world: World) -> None:
    async with connect(token_for(world.agent)):
        await wait_for_subscribers(world.agent.id, 1)

    await wait_for_subscribers(world.agent.id, 0)
