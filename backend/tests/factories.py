"""Helpers that create rows directly in the DB, for tests that aren't about how they're created."""

from datetime import UTC, datetime, timedelta
from itertools import count
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models import (
    AvailabilitySlot,
    Booking,
    BookingStatus,
    Listing,
    ListingImage,
    ListingStatus,
    PropertyType,
    User,
    UserRole,
)

_ids = count(1)


async def make_user(session: AsyncSession, role: UserRole = UserRole.AGENT) -> User:
    n = next(_ids)
    user = User(
        email=f"{role.value}{n}@example.com",
        password_hash="not-used",
        full_name=f"{role.value.title()} {n}",
        phone="+919800000000",
        role=role,
    )
    session.add(user)
    await session.commit()
    return user


def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


async def make_listing(
    session: AsyncSession,
    agent: User,
    *,
    image_urls: tuple[str, ...] = (),
    age_days: int = 0,
    **overrides: Any,
) -> Listing:
    values: dict[str, Any] = {
        "title": "Sunny 2 BHK Apartment",
        "description": "A bright apartment close to the metro.",
        "city": "Noida",
        "locality": "Sector 62",
        "address": "Flat 101, Tower A, Sector 62, Noida",
        "latitude": 28.627,
        "longitude": 77.372,
        "price": 8_000_000,
        "bhk": 2,
        "area_sqft": 1_000,
        "property_type": PropertyType.APARTMENT,
        "status": ListingStatus.ACTIVE,
        "created_at": datetime.now(UTC) - timedelta(days=age_days),
    }
    values.update(overrides)
    listing = Listing(agent_id=agent.id, **values)
    listing.images = [ListingImage(url=url, position=i) for i, url in enumerate(image_urls)]
    session.add(listing)
    await session.commit()
    return listing


def future_slot_start(days: int = 1, hour: int = 10) -> datetime:
    """A whole-hour UTC time `days` from now, safely in the future."""
    base = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    return base.replace(hour=hour) + timedelta(days=days)


async def make_slot(
    session: AsyncSession, listing: Listing, start: datetime, hours: int = 1
) -> AvailabilitySlot:
    slot = AvailabilitySlot(
        listing_id=listing.id, slot_start=start, slot_end=start + timedelta(hours=hours)
    )
    session.add(slot)
    await session.commit()
    return slot


async def make_booking(
    session: AsyncSession,
    listing: Listing,
    buyer: User,
    slot_start: datetime,
    status: BookingStatus = BookingStatus.PENDING,
) -> Booking:
    booking = Booking(
        listing_id=listing.id, buyer_id=buyer.id, slot_start=slot_start, status=status
    )
    session.add(booking)
    await session.commit()
    return booking


def listing_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "title": "Spacious 3 BHK Villa",
        "description": "Corner villa with a private garden and parking.",
        "city": "Gurugram",
        "locality": "Sector 56",
        "address": "House 12, Palm Grove, Sector 56, Gurugram",
        "latitude": 28.42,
        "longitude": 77.10,
        "price": 35_000_000,
        "bhk": 3,
        "area_sqft": 3_000,
        "property_type": "villa",
    }
    payload.update(overrides)
    return payload
