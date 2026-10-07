from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Listing, ListingStatus, User
from app.repositories.bookings import BookingRepository
from app.repositories.listings import ListingRepository
from app.repositories.slots import SlotRepository
from app.schemas.slots import HoldResponse, SlotCreateRequest, SlotResponse, SlotStatus
from app.services.slot_holds import SlotHoldStore

logger = structlog.get_logger(__name__)

# How far ahead the public slot list looks.
SLOT_LOOKAHEAD = timedelta(days=30)


class SlotService:
    def __init__(self, session: AsyncSession, holds: SlotHoldStore) -> None:
        self.session = session
        self.holds = holds
        self.listings = ListingRepository(session)
        self.slots = SlotRepository(session)
        self.bookings = BookingRepository(session)

    async def create_slots(
        self, agent: User, listing_id: int, data: SlotCreateRequest
    ) -> list[SlotResponse]:
        listing = await self._get_listing(listing_id)
        if listing.agent_id != agent.id:
            raise AppError("forbidden", "You can only add slots to your own listings", 403)

        now = datetime.now(UTC)
        ranges = [(s.slot_start, s.slot_end) for s in data.slots]
        if any(start <= now for start, _ in ranges):
            raise AppError("slot_in_past", "Slots must start in the future", 422)

        clashes = await self.slots.find_overlapping(listing.id, ranges)
        if clashes:
            raise AppError(
                "slot_overlap",
                f"Overlaps an existing slot starting {clashes[0].slot_start.isoformat()}",
                409,
            )

        created = await self.slots.create_many(listing.id, ranges)
        await self.session.commit()
        logger.info("slots_created", listing_id=listing.id, count=len(created))
        return [
            SlotResponse(
                id=s.id, slot_start=s.slot_start, slot_end=s.slot_end, status=SlotStatus.AVAILABLE
            )
            for s in created
        ]

    async def list_slots(self, listing_id: int) -> list[SlotResponse]:
        await self._get_listing(listing_id)
        now = datetime.now(UTC)
        rows = await self.slots.list_upcoming_with_booked_flag(
            listing_id, after=now, before=now + SLOT_LOOKAHEAD
        )
        held = await self.holds.held_slots(
            listing_id, [slot.slot_start for slot, booked in rows if not booked]
        )

        def status(slot_start: datetime, booked: bool) -> SlotStatus:
            if booked:
                return SlotStatus.BOOKED
            return SlotStatus.HELD if slot_start in held else SlotStatus.AVAILABLE

        return [
            SlotResponse(
                id=slot.id,
                slot_start=slot.slot_start,
                slot_end=slot.slot_end,
                status=status(slot.slot_start, booked),
            )
            for slot, booked in rows
        ]

    async def hold(self, buyer: User, listing_id: int, slot_start: datetime) -> HoldResponse:
        listing = await self._get_listing(listing_id)
        if listing.status is not ListingStatus.ACTIVE:
            raise AppError("listing_unavailable", "This listing is not taking visits", 409)

        slot = await self.slots.get(listing.id, slot_start)
        if slot is None:
            raise AppError("slot_not_found", "No such slot for this listing", 404)
        if slot.slot_start <= datetime.now(UTC):
            raise AppError("slot_in_past", "This slot has already started", 409)
        if await self.bookings.is_slot_booked(listing.id, slot.slot_start):
            raise AppError("slot_booked", "This slot has already been booked", 409)

        result = await self.holds.acquire(listing.id, slot.slot_start, buyer.id)
        if not result.acquired:
            raise AppError(
                "slot_held", "Another buyer is booking this slot. Try again in a few minutes.", 409
            )
        return HoldResponse(
            listing_id=listing.id,
            slot_start=slot.slot_start,
            expires_at=datetime.now(UTC) + timedelta(seconds=result.ttl_seconds),
            expires_in=result.ttl_seconds,
        )

    async def release_hold(self, buyer: User, listing_id: int, slot_start: datetime) -> None:
        # Idempotent: releasing a hold you don't have (or that already lapsed) is a no-op.
        await self.holds.release(listing_id, slot_start, buyer.id)

    async def _get_listing(self, listing_id: int) -> Listing:
        listing = await self.listings.get(listing_id)
        if listing is None:
            raise AppError("not_found", "Listing not found", 404)
        return listing
