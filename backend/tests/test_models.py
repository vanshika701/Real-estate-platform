"""Database-level guarantees: constraints that must hold no matter what the app code does."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AvailabilitySlot,
    Booking,
    BookingStatus,
    Listing,
    ListingImage,
    PropertyType,
    User,
    UserRole,
)

SLOT = datetime(2030, 1, 1, 10, 0, tzinfo=UTC)


async def _make_listing(session: AsyncSession) -> tuple[Listing, User, User]:
    agent = User(email="a@x.com", password_hash="x", full_name="Agent", role=UserRole.AGENT)
    buyer_1 = User(email="b1@x.com", password_hash="x", full_name="Buyer 1", role=UserRole.BUYER)
    buyer_2 = User(email="b2@x.com", password_hash="x", full_name="Buyer 2", role=UserRole.BUYER)
    listing = Listing(
        agent=agent,
        title="2 BHK",
        description="d",
        city="Noida",
        locality="Sector 62",
        address="addr",
        latitude=28.6,
        longitude=77.3,
        price=8_000_000,
        bhk=2,
        area_sqft=1_000,
        property_type=PropertyType.APARTMENT,
    )
    session.add_all([agent, buyer_1, buyer_2, listing])
    await session.commit()
    return listing, buyer_1, buyer_2


async def test_two_active_bookings_for_same_slot_are_rejected(db_session: AsyncSession) -> None:
    listing, buyer_1, buyer_2 = await _make_listing(db_session)
    db_session.add(Booking(listing_id=listing.id, buyer_id=buyer_1.id, slot_start=SLOT))
    await db_session.commit()

    db_session.add(Booking(listing_id=listing.id, buyer_id=buyer_2.id, slot_start=SLOT))
    with pytest.raises(IntegrityError, match="uq_bookings_active_slot"):
        await db_session.commit()


@pytest.mark.parametrize("freed_status", [BookingStatus.CANCELLED, BookingStatus.REJECTED])
async def test_cancelled_or_rejected_booking_frees_the_slot(
    db_session: AsyncSession, freed_status: BookingStatus
) -> None:
    listing, buyer_1, buyer_2 = await _make_listing(db_session)
    db_session.add(
        Booking(listing_id=listing.id, buyer_id=buyer_1.id, slot_start=SLOT, status=freed_status)
    )
    db_session.add(Booking(listing_id=listing.id, buyer_id=buyer_2.id, slot_start=SLOT))

    await db_session.commit()  # no IntegrityError

    count = await db_session.scalar(select(func.count()).select_from(Booking))
    assert count == 2


async def test_status_check_constraint_rejects_unknown_values(db_session: AsyncSession) -> None:
    listing, buyer_1, _ = await _make_listing(db_session)

    with pytest.raises(IntegrityError, match="ck_bookings_status_valid"):
        await db_session.execute(
            text(
                "INSERT INTO bookings (listing_id, buyer_id, slot_start, status) "
                "VALUES (:listing_id, :buyer_id, :slot_start, 'bogus')"
            ),
            {"listing_id": listing.id, "buyer_id": buyer_1.id, "slot_start": SLOT},
        )


async def test_slot_must_end_after_it_starts(db_session: AsyncSession) -> None:
    listing, _, _ = await _make_listing(db_session)
    db_session.add(
        AvailabilitySlot(listing_id=listing.id, slot_start=SLOT, slot_end=SLOT - timedelta(hours=1))
    )

    with pytest.raises(IntegrityError, match="ck_availability_slots_end_after_start"):
        await db_session.commit()


async def test_deleting_listing_cascades_to_images_slots_and_bookings(
    db_session: AsyncSession,
) -> None:
    listing, buyer_1, _ = await _make_listing(db_session)
    db_session.add_all(
        [
            ListingImage(listing_id=listing.id, url="http://img", position=0),
            AvailabilitySlot(
                listing_id=listing.id, slot_start=SLOT, slot_end=SLOT + timedelta(hours=1)
            ),
            Booking(listing_id=listing.id, buyer_id=buyer_1.id, slot_start=SLOT),
        ]
    )
    await db_session.commit()

    await db_session.execute(text("DELETE FROM listings WHERE id = :id"), {"id": listing.id})
    await db_session.commit()

    for model in (ListingImage, AvailabilitySlot, Booking):
        assert await db_session.scalar(select(func.count()).select_from(model)) == 0
