"""Populate the database with demo accounts, listings, images and availability slots.

Usage (from backend/):
    python -m scripts.seed          # no-op if demo data already exists
    python -m scripts.seed --reset  # wipe all tables and reseed
"""

import argparse
import asyncio
import random
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone

import structlog
from sqlalchemy import exists, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.models import (
    AvailabilitySlot,
    Base,
    Listing,
    ListingImage,
    ListingStatus,
    PropertyType,
    User,
    UserRole,
)
from scripts.seed_data import (
    CITIES,
    DEMO_AGENT,
    DEMO_BUYER,
    DEMO_PASSWORD,
    FEATURES,
    NEARBY,
    OTHER_AGENTS,
    SOCIETY_NAMES,
    TITLE_PREFIXES,
    City,
    Person,
)

logger = structlog.get_logger("seed")

IST = timezone(timedelta(hours=5, minutes=30))  # India has no DST, so a fixed offset is exact
SLOT_START_TIMES = (time(10), time(12), time(15), time(17))
SLOT_DAYS = 14
SLOT_DURATION = timedelta(hours=1)
IMAGES_PER_LISTING = (3, 5)
# Fixed seed: every machine (and every CI run) gets identical demo data.
RANDOM_SEED = 42

PROPERTY_TYPE_WEIGHTS = {
    PropertyType.APARTMENT: 65,
    PropertyType.INDEPENDENT_HOUSE: 15,
    PropertyType.VILLA: 10,
    PropertyType.PLOT: 10,
}


@dataclass(frozen=True)
class SeedSummary:
    users: int
    listings: int
    images: int
    slots: int


def _pick_property(rng: random.Random) -> tuple[PropertyType, int, int, float]:
    """Return (type, bhk, area_sqft, price multiplier relative to the city's base rate)."""
    types, weights = zip(*PROPERTY_TYPE_WEIGHTS.items(), strict=True)
    ptype = rng.choices(types, weights=weights)[0]
    if ptype is PropertyType.PLOT:
        return ptype, 0, rng.randrange(1_000, 4_000, 50), 0.6
    if ptype is PropertyType.VILLA:
        bhk = rng.randint(3, 5)
        return ptype, bhk, rng.randrange(2_500, 5_000, 50), 1.25
    if ptype is PropertyType.INDEPENDENT_HOUSE:
        bhk = rng.randint(2, 5)
        return ptype, bhk, rng.randrange(1_200 + bhk * 300, 2_000 + bhk * 400, 50), 1.1
    bhk = rng.choices((1, 2, 3, 4), weights=(15, 35, 35, 15))[0]
    base_area = {1: 550, 2: 950, 3: 1_400, 4: 2_000}[bhk]
    return ptype, bhk, rng.randrange(base_area, int(base_area * 1.35), 25), 1.0


def _title(rng: random.Random, ptype: PropertyType, bhk: int, area: int, locality: str) -> str:
    if ptype is PropertyType.PLOT:
        return f"{area:,} sq ft Residential Plot in {locality}"
    label = {
        PropertyType.APARTMENT: "Apartment",
        PropertyType.VILLA: "Villa",
        PropertyType.INDEPENDENT_HOUSE: "Independent House",
    }[ptype]
    return f"{rng.choice(TITLE_PREFIXES)} {bhk} BHK {label} in {locality}"


def _description(rng: random.Random, ptype: PropertyType, locality: str, city: str) -> str:
    near = ", ".join(rng.sample(NEARBY, 2))
    if ptype is PropertyType.PLOT:
        return (
            f"Clear-title residential plot in {locality}, {city}, in a gated layout with "
            f"wide internal roads, street lighting and water and power connections ready. "
            f"Close to {near}. Suitable for building a custom home."
        )
    features = ", ".join(rng.sample(FEATURES, 3))
    furnishing = rng.choice(("Semi-furnished", "Unfurnished", "Fully furnished"))
    highlight = rng.choice(
        ("vastu-compliant layout", "abundant natural light", "cross ventilation")
    )
    return (
        f"A well-maintained home in {locality}, {city}, with {features}. "
        f"Located within easy reach of {near}. {furnishing}, with {highlight}."
    )


def _address(rng: random.Random, ptype: PropertyType, locality: str, city: str) -> str:
    if ptype is PropertyType.APARTMENT:
        tower = rng.choice("ABCDEFGH")
        flat = rng.randint(1, 25) * 100 + rng.randint(1, 8)
        return f"Flat {flat}, Tower {tower}, {rng.choice(SOCIETY_NAMES)}, {locality}, {city}"
    return f"House {rng.randint(1, 450)}, {rng.choice(SOCIETY_NAMES)}, {locality}, {city}"


def _round_price(value: float) -> int:
    """Round to the nearest ₹50,000, how Indian listings are usually quoted."""
    return max(50_000, round(value / 50_000) * 50_000)


def _build_listing(rng: random.Random, city: City, agent: User, now: datetime) -> Listing:
    locality = rng.choice(city.localities)
    ptype, bhk, area, multiplier = _pick_property(rng)
    rate = rng.randint(*city.rate_per_sqft) * multiplier
    created_at = now - timedelta(days=rng.randint(0, 60), hours=rng.randint(0, 23))
    status = rng.choices(
        (ListingStatus.ACTIVE, ListingStatus.SOLD, ListingStatus.INACTIVE), weights=(88, 7, 5)
    )[0]

    return Listing(
        agent=agent,
        title=_title(rng, ptype, bhk, area, locality.name),
        description=_description(rng, ptype, locality.name, city.name),
        city=city.name,
        locality=locality.name,
        address=_address(rng, ptype, locality.name, city.name),
        # Jitter within ~1 km so pins in the same locality don't stack on the map.
        latitude=round(locality.lat + rng.uniform(-0.009, 0.009), 6),
        longitude=round(locality.lng + rng.uniform(-0.009, 0.009), 6),
        price=_round_price(area * rate),
        bhk=bhk,
        area_sqft=area,
        property_type=ptype,
        status=status,
        created_at=created_at,
        updated_at=created_at,
    )


def _build_images(rng: random.Random, listing_no: int) -> list[ListingImage]:
    count = rng.randint(*IMAGES_PER_LISTING)
    return [
        ListingImage(
            url=f"https://picsum.photos/seed/propvisit-{listing_no}-{i}/1200/800", position=i
        )
        for i in range(count)
    ]


def _build_slots(rng: random.Random, start_day: date) -> list[AvailabilitySlot]:
    slots = []
    for offset in range(SLOT_DAYS):
        day = start_day + timedelta(days=offset)
        # Agents aren't available every day or every hour; vary it so the picker looks real.
        if rng.random() < 0.2:
            continue
        for start_time in sorted(rng.sample(SLOT_START_TIMES, rng.randint(2, 4))):
            start = datetime.combine(day, start_time, tzinfo=IST)
            slots.append(AvailabilitySlot(slot_start=start, slot_end=start + SLOT_DURATION))
    return slots


def _make_user(person: Person, role: UserRole, password_hash: str) -> User:
    return User(
        email=person.email,
        full_name=person.full_name,
        phone=person.phone,
        role=role,
        password_hash=password_hash,
    )


async def is_seeded(session: AsyncSession) -> bool:
    return bool(await session.scalar(select(exists().where(User.email == DEMO_BUYER.email))))


async def reset(session: AsyncSession) -> None:
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    await session.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    await session.commit()


async def seed(session: AsyncSession, now: datetime | None = None) -> SeedSummary:
    rng = random.Random(RANDOM_SEED)  # noqa: S311 - not used for anything security-related
    now = now or datetime.now(UTC)

    # bcrypt is deliberately slow; every demo account shares a password, so hash it once.
    password_hash = hash_password(DEMO_PASSWORD)
    buyer = _make_user(DEMO_BUYER, UserRole.BUYER, password_hash)
    demo_agent = _make_user(DEMO_AGENT, UserRole.AGENT, password_hash)
    other_agents = [_make_user(p, UserRole.AGENT, password_hash) for p in OTHER_AGENTS]
    session.add_all([buyer, demo_agent, *other_agents])

    first_slot_day = now.astimezone(IST).date() + timedelta(days=1)
    listings: list[Listing] = []
    image_count = slot_count = 0
    for city in CITIES:
        for _ in range(city.listing_count):
            # The demo agent gets a larger share so their dashboard has plenty to show.
            agent = demo_agent if rng.random() < 0.3 else rng.choice(other_agents)
            listing = _build_listing(rng, city, agent, now)
            images = _build_images(rng, len(listings))
            # Sold/inactive listings take no visits, so they get no slots.
            slots = (
                _build_slots(rng, first_slot_day) if listing.status is ListingStatus.ACTIVE else []
            )
            listing.images, listing.slots = images, slots
            image_count += len(images)
            slot_count += len(slots)
            listings.append(listing)

    session.add_all(listings)
    await session.commit()

    return SeedSummary(
        users=2 + len(other_agents), listings=len(listings), images=image_count, slots=slot_count
    )


async def main(reset_first: bool) -> None:
    configure_logging(get_settings().log_level, json_logs=get_settings().app_env == "production")
    try:
        async with SessionLocal() as session:
            if reset_first:
                await reset(session)
                logger.info("seed_reset")
            elif await is_seeded(session):
                logger.info("seed_skipped", reason="demo data already present")
                return
            summary = await seed(session)
            logger.info("seed_complete", **summary.__dict__)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed PropVisit with demo data.")
    parser.add_argument("--reset", action="store_true", help="wipe all tables before seeding")
    asyncio.run(main(parser.parse_args().reset))
