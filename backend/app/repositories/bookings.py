from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import Select, exists, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import ACTIVE_BOOKING_STATUSES, Booking, BookingStatus, Listing


class BookingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def is_slot_booked(self, listing_id: int, slot_start: datetime) -> bool:
        query = select(
            exists().where(
                Booking.listing_id == listing_id,
                Booking.slot_start == slot_start,
                Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            )
        )
        return bool(await self.session.scalar(query))

    async def create(
        self, listing_id: int, buyer_id: int, slot_start: datetime, note: str | None
    ) -> Booking:
        booking = Booking(
            listing_id=listing_id, buyer_id=buyer_id, slot_start=slot_start, note=note
        )
        self.session.add(booking)
        await self.session.flush()  # raises IntegrityError if the slot is already taken
        return booking

    @staticmethod
    def _with_details() -> Select[tuple[Booking]]:
        return select(Booking).options(
            joinedload(Booking.listing).joinedload(Listing.agent), joinedload(Booking.buyer)
        )

    async def get_detailed(self, booking_id: int) -> Booking | None:
        return await self.session.scalar(
            self._with_details()
            .where(Booking.id == booking_id)
            .execution_options(populate_existing=True)
        )

    async def list_for_buyer(self, buyer_id: int) -> list[Booking]:
        rows = await self.session.scalars(
            self._with_details()
            .where(Booking.buyer_id == buyer_id)
            .order_by(Booking.slot_start.desc(), Booking.id.desc())
        )
        return list(rows)

    async def list_for_agent(
        self, agent_id: int, status: BookingStatus | None, page: int, page_size: int
    ) -> tuple[list[Booking], int]:
        conditions = [Listing.agent_id == agent_id]
        if status is not None:
            conditions.append(Booking.status == status)

        total = await self.session.scalar(
            select(func.count()).select_from(Booking).join(Listing).where(*conditions)
        )
        rows = await self.session.scalars(
            self._with_details()
            .join(Booking.listing)
            .where(*conditions)
            .order_by(Booking.slot_start.asc(), Booking.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(rows), total or 0

    async def transition(
        self, booking_id: int, allowed_from: Iterable[BookingStatus], to: BookingStatus
    ) -> bool:
        """Change status only if it is still one of `allowed_from`. Returns whether it changed.

        The check and the write are one UPDATE statement, so two racing requests (say, a buyer
        cancelling while the agent accepts) can't both succeed: the second matches no row.
        """
        result = await self.session.execute(
            update(Booking)
            .where(Booking.id == booking_id, Booking.status.in_(list(allowed_from)))
            .values(status=to)
        )
        return result.rowcount == 1  # type: ignore[attr-defined]
