import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_client
from app.models import Booking, BookingStatus, Listing, User, UserRole
from app.services.slot_holds import SlotHoldStore
from tests.factories import (
    auth_headers,
    future_slot_start,
    make_booking,
    make_listing,
    make_slot,
    make_user,
)


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


async def hold(client: AsyncClient, w: World, buyer: User) -> Response:
    return await client.post(
        f"/api/v1/listings/{w.listing.id}/slots/hold",
        json={"slot_start": w.slot_start.isoformat()},
        headers=auth_headers(buyer),
    )


async def book(client: AsyncClient, w: World, buyer: User, note: str | None = None) -> Response:
    return await client.post(
        "/api/v1/bookings",
        json={"listing_id": w.listing.id, "slot_start": w.slot_start.isoformat(), "note": note},
        headers=auth_headers(buyer),
    )


async def active_bookings(session: AsyncSession, listing_id: int) -> int:
    count = await session.scalar(
        select(func.count())
        .select_from(Booking)
        .where(
            Booking.listing_id == listing_id,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.ACCEPTED]),
        )
    )
    return count or 0


# --- happy path -----------------------------------------------------------------------------


async def test_hold_then_book_creates_pending_booking(client: AsyncClient, world: World) -> None:
    await hold(client, world, world.buyer)

    response = await book(client, world, world.buyer, note="  Please call before  ")

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["note"] == "Please call before"
    assert body["listing"]["title"] == world.listing.title
    # The hold is consumed and the slot now shows as booked.
    assert await redis_client.get(SlotHoldStore.key(world.listing.id, world.slot_start)) is None
    slots = (await client.get(f"/api/v1/listings/{world.listing.id}/slots")).json()
    assert slots[0]["status"] == "booked"


async def test_my_bookings_lists_only_mine(
    client: AsyncClient, world: World, db_session: AsyncSession
) -> None:
    await hold(client, world, world.buyer)
    mine = (await book(client, world, world.buyer)).json()
    later = future_slot_start(days=2)
    await make_slot(db_session, world.listing, later)
    await make_booking(db_session, world.listing, world.other_buyer, later)

    response = await client.get("/api/v1/bookings/me", headers=auth_headers(world.buyer))

    assert response.status_code == 200
    assert [b["id"] for b in response.json()] == [mine["id"]]


# --- the double-booking guarantees ----------------------------------------------------------


async def test_booking_requires_holding_the_slot(client: AsyncClient, world: World) -> None:
    response = await book(client, world, world.buyer)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "hold_required"


async def test_cannot_book_with_someone_elses_hold(client: AsyncClient, world: World) -> None:
    await hold(client, world, world.buyer)

    response = await book(client, world, world.other_buyer)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "hold_required"


async def test_database_rejects_second_booking_even_with_a_valid_hold(
    client: AsyncClient, world: World, db_session: AsyncSession
) -> None:
    """Simulates the hold layer failing (e.g. a hold lapsed and was re-taken mid-booking)."""
    await hold(client, world, world.buyer)
    assert (await book(client, world, world.buyer)).status_code == 201
    # Give the second buyer a hold directly, as if Redis had let it through.
    await redis_client.set(
        SlotHoldStore.key(world.listing.id, world.slot_start), str(world.other_buyer.id)
    )

    response = await book(client, world, world.other_buyer)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "slot_booked"
    assert await active_bookings(db_session, world.listing.id) == 1


class _AnyBuyer:
    """Compares equal to every buyer ID."""

    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False

    __hash__ = None  # type: ignore[assignment]


class _PermissiveHolds:
    """A hold store that says every buyer holds every slot: the Redis layer switched off."""

    async def holder(self, listing_id: int, slot_start: datetime) -> Any:
        return _AnyBuyer()

    async def release(self, listing_id: int, slot_start: datetime, buyer_id: int) -> bool:
        return True


async def test_two_buyers_can_never_book_the_same_slot_concurrently(
    client: AsyncClient, world: World, db_session: AsyncSession
) -> None:
    """The definition-of-done test. With the Redis hold check switched off, both requests
    reach the INSERT together; the partial unique index alone must let exactly one through."""
    from app.api.deps import get_hold_store
    from app.main import app

    app.dependency_overrides[get_hold_store] = lambda: _PermissiveHolds()

    for day in range(2, 7):  # several fresh slots, to give the race a fair chance to show up
        world.slot_start = future_slot_start(days=day)
        await make_slot(db_session, world.listing, world.slot_start)

        responses = await asyncio.gather(
            book(client, world, world.buyer), book(client, world, world.other_buyer)
        )

        assert sorted(r.status_code for r in responses) == [201, 409]
        loser = next(r for r in responses if r.status_code == 409)
        assert loser.json()["error"]["code"] == "slot_booked"

    assert await active_bookings(db_session, world.listing.id) == 5


async def test_cancelled_slot_can_be_booked_again(
    client: AsyncClient, world: World, db_session: AsyncSession
) -> None:
    await make_booking(
        db_session, world.listing, world.buyer, world.slot_start, BookingStatus.CANCELLED
    )
    await hold(client, world, world.other_buyer)

    response = await book(client, world, world.other_buyer)

    assert response.status_code == 201


async def test_note_length_is_limited(client: AsyncClient, world: World) -> None:
    await hold(client, world, world.buyer)

    response = await book(client, world, world.buyer, note="x" * 501)

    assert response.status_code == 422


# --- cancelling -----------------------------------------------------------------------------


async def test_buyer_cancels_own_booking_and_slot_frees_up(
    client: AsyncClient, world: World
) -> None:
    await hold(client, world, world.buyer)
    booking = (await book(client, world, world.buyer)).json()

    response = await client.patch(
        f"/api/v1/bookings/{booking['id']}/cancel", headers=auth_headers(world.buyer)
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    slots = (await client.get(f"/api/v1/listings/{world.listing.id}/slots")).json()
    assert slots[0]["status"] == "available"


async def test_cannot_cancel_twice(
    client: AsyncClient, world: World, db_session: AsyncSession
) -> None:
    booking = await make_booking(db_session, world.listing, world.buyer, world.slot_start)
    url = f"/api/v1/bookings/{booking.id}/cancel"

    await client.patch(url, headers=auth_headers(world.buyer))
    response = await client.patch(url, headers=auth_headers(world.buyer))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_status"


async def test_cannot_cancel_someone_elses_booking(
    client: AsyncClient, world: World, db_session: AsyncSession
) -> None:
    booking = await make_booking(db_session, world.listing, world.buyer, world.slot_start)

    response = await client.patch(
        f"/api/v1/bookings/{booking.id}/cancel", headers=auth_headers(world.other_buyer)
    )

    assert response.status_code == 404


async def test_cannot_cancel_past_visit(
    client: AsyncClient, world: World, db_session: AsyncSession
) -> None:
    past = datetime.now(UTC) - timedelta(days=1)
    booking = await make_booking(db_session, world.listing, world.buyer, past)

    response = await client.patch(
        f"/api/v1/bookings/{booking.id}/cancel", headers=auth_headers(world.buyer)
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "visit_started"


# --- agent side -----------------------------------------------------------------------------


async def test_agent_sees_bookings_for_own_listings_with_buyer_contact(
    client: AsyncClient, world: World, db_session: AsyncSession
) -> None:
    mine = await make_booking(db_session, world.listing, world.buyer, world.slot_start)
    other_agent = await make_user(db_session, UserRole.AGENT)
    other_listing = await make_listing(db_session, other_agent)
    await make_booking(db_session, other_listing, world.other_buyer, world.slot_start)

    response = await client.get("/api/v1/agent/bookings", headers=auth_headers(world.agent))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id"] == mine.id
    assert item["buyer"]["email"] == world.buyer.email
    assert item["buyer"]["phone"] == world.buyer.phone


async def test_agent_bookings_filter_by_status(
    client: AsyncClient, world: World, db_session: AsyncSession
) -> None:
    pending = await make_booking(db_session, world.listing, world.buyer, world.slot_start)
    await make_booking(
        db_session, world.listing, world.other_buyer, world.slot_start, BookingStatus.REJECTED
    )

    response = await client.get(
        "/api/v1/agent/bookings", params={"status": "pending"}, headers=auth_headers(world.agent)
    )

    assert [b["id"] for b in response.json()["items"]] == [pending.id]


@pytest.mark.parametrize("decision", ["accepted", "rejected"])
async def test_agent_accepts_or_rejects_pending_booking(
    client: AsyncClient, world: World, db_session: AsyncSession, decision: str
) -> None:
    booking = await make_booking(db_session, world.listing, world.buyer, world.slot_start)

    response = await client.patch(
        f"/api/v1/agent/bookings/{booking.id}",
        json={"status": decision},
        headers=auth_headers(world.agent),
    )

    assert response.status_code == 200
    assert response.json()["status"] == decision


async def test_agent_cannot_decide_twice_or_after_buyer_cancels(
    client: AsyncClient, world: World, db_session: AsyncSession
) -> None:
    cancelled = await make_booking(
        db_session, world.listing, world.buyer, world.slot_start, BookingStatus.CANCELLED
    )

    response = await client.patch(
        f"/api/v1/agent/bookings/{cancelled.id}",
        json={"status": "accepted"},
        headers=auth_headers(world.agent),
    )

    assert response.status_code == 409
    assert "cancelled" in response.json()["error"]["message"]


async def test_agent_cannot_decide_on_other_agents_bookings(
    client: AsyncClient, world: World, db_session: AsyncSession
) -> None:
    booking = await make_booking(db_session, world.listing, world.buyer, world.slot_start)
    other_agent = await make_user(db_session, UserRole.AGENT)

    response = await client.patch(
        f"/api/v1/agent/bookings/{booking.id}",
        json={"status": "accepted"},
        headers=auth_headers(other_agent),
    )

    assert response.status_code == 404


async def test_agent_cannot_set_arbitrary_status(
    client: AsyncClient, world: World, db_session: AsyncSession
) -> None:
    booking = await make_booking(db_session, world.listing, world.buyer, world.slot_start)

    response = await client.patch(
        f"/api/v1/agent/bookings/{booking.id}",
        json={"status": "cancelled"},
        headers=auth_headers(world.agent),
    )

    assert response.status_code == 422


async def test_buyers_cannot_use_agent_endpoints(client: AsyncClient, world: World) -> None:
    response = await client.get("/api/v1/agent/bookings", headers=auth_headers(world.buyer))

    assert response.status_code == 403


async def test_agent_stats_count_only_own_relevant_items(
    client: AsyncClient, world: World, db_session: AsyncSession
) -> None:
    from app.models import ListingStatus

    await make_listing(db_session, world.agent, status=ListingStatus.SOLD)
    await make_booking(db_session, world.listing, world.buyer, world.slot_start)  # pending
    upcoming = future_slot_start(days=2)
    await make_booking(
        db_session, world.listing, world.other_buyer, upcoming, BookingStatus.ACCEPTED
    )
    past = datetime.now(UTC) - timedelta(days=2)
    await make_booking(db_session, world.listing, world.buyer, past, BookingStatus.ACCEPTED)
    other_agent = await make_user(db_session, UserRole.AGENT)
    other_listing = await make_listing(db_session, other_agent)
    await make_booking(db_session, other_listing, world.buyer, world.slot_start)

    response = await client.get("/api/v1/agent/stats", headers=auth_headers(world.agent))

    assert response.status_code == 200
    assert response.json() == {"active_listings": 1, "pending_requests": 1, "upcoming_visits": 1}
