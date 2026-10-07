from datetime import datetime

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ACTIVE_BOOKING_STATUSES, AvailabilitySlot, Booking


class SlotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_overlapping(
        self, listing_id: int, ranges: list[tuple[datetime, datetime]]
    ) -> list[AvailabilitySlot]:
        """Existing slots that overlap any of the given [start, end) ranges."""
        overlaps = [
            and_(AvailabilitySlot.slot_start < end, AvailabilitySlot.slot_end > start)
            for start, end in ranges
        ]
        rows = await self.session.scalars(
            select(AvailabilitySlot).where(
                AvailabilitySlot.listing_id == listing_id, or_(*overlaps)
            )
        )
        return list(rows)

    async def create_many(
        self, listing_id: int, ranges: list[tuple[datetime, datetime]]
    ) -> list[AvailabilitySlot]:
        slots = [
            AvailabilitySlot(listing_id=listing_id, slot_start=start, slot_end=end)
            for start, end in ranges
        ]
        self.session.add_all(slots)
        await self.session.flush()
        return slots

    async def get(self, listing_id: int, slot_start: datetime) -> AvailabilitySlot | None:
        return await self.session.scalar(
            select(AvailabilitySlot).where(
                AvailabilitySlot.listing_id == listing_id,
                AvailabilitySlot.slot_start == slot_start,
            )
        )

    async def list_upcoming_with_booked_flag(
        self, listing_id: int, after: datetime, before: datetime
    ) -> list[tuple[AvailabilitySlot, bool]]:
        is_booked = (
            exists()
            .where(
                Booking.listing_id == AvailabilitySlot.listing_id,
                Booking.slot_start == AvailabilitySlot.slot_start,
                Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            )
            .correlate(AvailabilitySlot)
        )
        rows = await self.session.execute(
            select(AvailabilitySlot, is_booked)
            .where(
                AvailabilitySlot.listing_id == listing_id,
                AvailabilitySlot.slot_start > after,
                AvailabilitySlot.slot_start < before,
            )
            .order_by(AvailabilitySlot.slot_start)
        )
        return [(slot, booked) for slot, booked in rows.all()]
