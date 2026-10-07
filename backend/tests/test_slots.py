import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_client
from app.models import BookingStatus, Listing, ListingStatus, User, UserRole
from app.services.slot_holds import SlotHoldStore
from tests.factories import (
    auth_headers,
    future_slot_start,
    make_booking,
    make_listing,
    make_slot,
    make_user,
)

IST = timezone(timedelta(hours=5, minutes=30))


@dataclass
class World:
    agent: User
    buyer: User
    other_buyer: User
    listing: Listing
    slot_start: datetime


@pytest.fixture
async def world(db_session: AsyncSession) -> World:
    agent = await make_user(db_session, UserRole.AGENT)
    buyer = await make_user(db_session, UserRole.BUYER)
    other_buyer = await make_user(db_session, UserRole.BUYER)
    listing = await make_listing(db_session, agent)
    start = future_slot_start()
    await make_slot(db_session, listing, start)
    return World(agent, buyer, other_buyer, listing, start)


def slots_url(listing_id: int) -> str:
    return f"/api/v1/listings/{listing_id}/slots"


def iso(dt: datetime) -> str:
    return dt.isoformat()


async def hold(client: AsyncClient, w: World, buyer: User, start: datetime | None = None) -> Any:
    return await client.post(
        f"{slots_url(w.listing.id)}/hold",
        json={"slot_start": iso(start or w.slot_start)},
        headers=auth_headers(buyer),
    )


async def slot_statuses(client: AsyncClient, listing_id: int) -> dict[str, str]:
    response = await client.get(slots_url(listing_id))
    assert response.status_code == 200
    return {
        datetime.fromisoformat(s["slot_start"]).isoformat(): s["status"] for s in response.json()
    }


# --- creating slots -------------------------------------------------------------------------


async def test_agent_creates_slots_for_own_listing(client: AsyncClient, world: World) -> None:
    start = future_slot_start(days=2)
    payload = {
        "slots": [
            {"slot_start": iso(start), "slot_end": iso(start + timedelta(hours=1))},
            {
                "slot_start": iso(start + timedelta(hours=2)),
                "slot_end": iso(start + timedelta(hours=3)),
            },
        ]
    }

    response = await client.post(
        slots_url(world.listing.id), json=payload, headers=auth_headers(world.agent)
    )

    assert response.status_code == 201
    assert [s["status"] for s in response.json()] == ["available", "available"]
    assert len(await slot_statuses(client, world.listing.id)) == 3


async def test_other_agent_cannot_create_slots(
    client: AsyncClient, world: World, db_session: AsyncSession
) -> None:
    other = await make_user(db_session, UserRole.AGENT)
    start = future_slot_start(days=3)
    payload = {"slots": [{"slot_start": iso(start), "slot_end": iso(start + timedelta(hours=1))}]}

    response = await client.post(
        slots_url(world.listing.id), json=payload, headers=auth_headers(other)
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("slots", "status", "code"),
    [
        # in the past
        ([(-1, 0, 1)], 422, "slot_in_past"),
        # too short / too long
        ([(3, 0, 0.1)], 422, "validation_error"),
        ([(3, 0, 5)], 422, "validation_error"),
        # overlapping within the request
        ([(3, 0, 1), (3, 0.5, 1)], 422, "validation_error"),
        # overlapping the existing slot (world.slot_start is day 1, 10:00, 1 hour)
        ([(1, 0.5, 1)], 409, "slot_overlap"),
    ],
)
async def test_slot_creation_validation(
    client: AsyncClient,
    world: World,
    slots: list[tuple[int, float, float]],
    status: int,
    code: str,
) -> None:
    base = future_slot_start(days=0)
    payload = {
        "slots": [
            {
                "slot_start": iso(base + timedelta(days=d, hours=offset)),
                "slot_end": iso(base + timedelta(days=d, hours=offset + length)),
            }
            for d, offset, length in slots
        ]
    }

    response = await client.post(
        slots_url(world.listing.id), json=payload, headers=auth_headers(world.agent)
    )

    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code


async def test_naive_datetimes_are_rejected(client: AsyncClient, world: World) -> None:
    payload = {"slots": [{"slot_start": "2030-01-01T10:00:00", "slot_end": "2030-01-01T11:00:00"}]}

    response = await client.post(
        slots_url(world.listing.id), json=payload, headers=auth_headers(world.agent)
    )

    assert response.status_code == 422


# --- listing slots --------------------------------------------------------------------------


async def test_slot_list_shows_available_held_and_booked(
    client: AsyncClient, world: World, db_session: AsyncSession
) -> None:
    held_start = future_slot_start(days=2)
    booked_start = future_slot_start(days=3)
    await make_slot(db_session, world.listing, held_start)
    await make_slot(db_session, world.listing, booked_start)
    await make_booking(db_session, world.listing, world.other_buyer, booked_start)
    await hold(client, world, world.buyer, held_start)

    statuses = await slot_statuses(client, world.listing.id)

    assert statuses == {
        world.slot_start.isoformat(): "available",
        held_start.isoformat(): "held",
        booked_start.isoformat(): "booked",
    }


async def test_slot_list_hides_past_slots(
    client: AsyncClient, world: World, db_session: AsyncSession
) -> None:
    await make_slot(db_session, world.listing, datetime.now(UTC) - timedelta(days=1))

    assert list(await slot_statuses(client, world.listing.id)) == [world.slot_start.isoformat()]


async def test_cancelled_booking_frees_slot_in_list(
    client: AsyncClient, world: World, db_session: AsyncSession
) -> None:
    await make_booking(
        db_session, world.listing, world.buyer, world.slot_start, BookingStatus.CANCELLED
    )

    statuses = await slot_statuses(client, world.listing.id)

    assert statuses[world.slot_start.isoformat()] == "available"


# --- holds ----------------------------------------------------------------------------------


async def test_buyer_can_hold_slot_for_five_minutes(client: AsyncClient, world: World) -> None:
    response = await hold(client, world, world.buyer)

    assert response.status_code == 200
    body = response.json()
    assert body["expires_in"] == 300
    key = SlotHoldStore.key(world.listing.id, world.slot_start)
    assert await redis_client.get(key) == str(world.buyer.id)
    assert 295 <= await redis_client.ttl(key) <= 300


async def test_second_buyer_cannot_hold_held_slot(client: AsyncClient, world: World) -> None:
    await hold(client, world, world.buyer)

    response = await hold(client, world, world.other_buyer)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "slot_held"


async def test_concurrent_holds_exactly_one_wins(client: AsyncClient, world: World) -> None:
    responses = await asyncio.gather(
        *(hold(client, world, buyer) for buyer in (world.buyer, world.other_buyer))
    )

    assert sorted(r.status_code for r in responses) == [200, 409]


async def test_same_instant_in_another_timezone_is_the_same_hold(
    client: AsyncClient, world: World
) -> None:
    await hold(client, world, world.buyer)

    response = await hold(client, world, world.other_buyer, world.slot_start.astimezone(IST))

    assert response.status_code == 409


async def test_rehold_by_same_buyer_does_not_extend_hold(client: AsyncClient, world: World) -> None:
    await hold(client, world, world.buyer)
    key = SlotHoldStore.key(world.listing.id, world.slot_start)
    await redis_client.expire(key, 100)  # pretend 200 seconds have passed

    response = await hold(client, world, world.buyer)

    assert response.status_code == 200
    assert response.json()["expires_in"] <= 100


@pytest.mark.parametrize(
    ("setup", "status", "code"),
    [
        ("unknown_slot", 404, "slot_not_found"),
        ("booked", 409, "slot_booked"),
        ("inactive_listing", 409, "listing_unavailable"),
    ],
)
async def test_hold_rejections(
    client: AsyncClient,
    world: World,
    db_session: AsyncSession,
    setup: str,
    status: int,
    code: str,
) -> None:
    start = world.slot_start
    if setup == "unknown_slot":
        start = world.slot_start + timedelta(minutes=30)
    elif setup == "booked":
        await make_booking(db_session, world.listing, world.other_buyer, world.slot_start)
    else:
        world.listing.status = ListingStatus.INACTIVE
        await db_session.commit()

    response = await hold(client, world, world.buyer, start)

    assert response.status_code == status
    assert response.json()["error"]["code"] == code


async def test_agents_cannot_hold(client: AsyncClient, world: World) -> None:
    response = await hold(client, world, world.agent)

    assert response.status_code == 403


async def test_buyer_can_release_own_hold(client: AsyncClient, world: World) -> None:
    await hold(client, world, world.buyer)

    response = await client.request(
        "DELETE",
        f"{slots_url(world.listing.id)}/hold",
        json={"slot_start": iso(world.slot_start)},
        headers=auth_headers(world.buyer),
    )

    assert response.status_code == 204
    assert (await hold(client, world, world.other_buyer)).status_code == 200


async def test_buyer_cannot_release_someone_elses_hold(client: AsyncClient, world: World) -> None:
    await hold(client, world, world.buyer)

    await client.request(
        "DELETE",
        f"{slots_url(world.listing.id)}/hold",
        json={"slot_start": iso(world.slot_start)},
        headers=auth_headers(world.other_buyer),
    )

    assert (await hold(client, world, world.other_buyer)).status_code == 409


class _RedisDown:
    def __getattr__(self, name: str) -> Any:
        from redis.exceptions import ConnectionError as RedisConnectionError

        def fail(*args: Any, **kwargs: Any) -> Any:
            raise RedisConnectionError("down")

        return fail


async def test_holds_fail_closed_with_503_when_redis_is_down(
    client: AsyncClient, world: World
) -> None:
    from app.api.deps import get_hold_store
    from app.main import app

    store = SlotHoldStore.__new__(SlotHoldStore)
    store.redis = _RedisDown()  # type: ignore[assignment]
    store.ttl_seconds = 300
    app.dependency_overrides[get_hold_store] = lambda: store

    response = await hold(client, world, world.buyer)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"
