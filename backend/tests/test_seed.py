from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models import AvailabilitySlot, Listing, ListingStatus, User, UserRole
from scripts.seed import is_seeded, seed
from scripts.seed_data import DEMO_PASSWORD

NOW = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)


async def test_seed_creates_demo_accounts_with_working_password(db_session: AsyncSession) -> None:
    await seed(db_session, now=NOW)

    buyer = await db_session.scalar(select(User).where(User.email == "buyer@demo.com"))
    agent = await db_session.scalar(select(User).where(User.email == "agent@demo.com"))
    assert buyer is not None and buyer.role is UserRole.BUYER
    assert agent is not None and agent.role is UserRole.AGENT
    assert verify_password(DEMO_PASSWORD, buyer.password_hash)


async def test_seed_creates_realistic_listings_across_cities(db_session: AsyncSession) -> None:
    summary = await seed(db_session, now=NOW)

    assert 45 <= summary.listings <= 55
    cities = set(await db_session.scalars(select(Listing.city).distinct()))
    assert cities == {
        "Greater Noida",
        "Noida",
        "Gurugram",
        "Delhi",
        "Bengaluru",
        "Pune",
        "Mumbai",
    }
    demo_agent_listings = await db_session.scalar(
        select(func.count()).select_from(Listing).join(User).where(User.email == "agent@demo.com")
    )
    assert demo_agent_listings and demo_agent_listings >= 5


async def test_seed_slots_cover_next_14_days_for_active_listings_only(
    db_session: AsyncSession,
) -> None:
    await seed(db_session, now=NOW)

    first, last = (
        await db_session.execute(
            select(func.min(AvailabilitySlot.slot_start), func.max(AvailabilitySlot.slot_start))
        )
    ).one()
    assert first > NOW
    assert (last - NOW).days <= 14

    inactive_with_slots = await db_session.scalar(
        select(func.count())
        .select_from(AvailabilitySlot)
        .join(Listing)
        .where(Listing.status != ListingStatus.ACTIVE)
    )
    assert inactive_with_slots == 0


async def test_is_seeded_reflects_database_state(db_session: AsyncSession) -> None:
    assert not await is_seeded(db_session)
    await seed(db_session, now=NOW)
    assert await is_seeded(db_session)
