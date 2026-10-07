from datetime import UTC, datetime

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import ACTIVE_BOOKING_STATUSES, Booking, BookingStatus, ListingStatus, User
from app.repositories.bookings import BookingRepository
from app.repositories.listings import ListingRepository
from app.repositories.slots import SlotRepository
from app.schemas.bookings import (
    AgentBookingDecision,
    AgentBookingPage,
    AgentBookingResponse,
    AgentStats,
    BookingCreate,
    BookingResponse,
)
from app.services.notifications import BookingNotifier
from app.services.slot_holds import SlotHoldStore

logger = structlog.get_logger(__name__)

ACTIVE_BOOKING_INDEX = "uq_bookings_active_slot"


class BookingService:
    def __init__(
        self, session: AsyncSession, holds: SlotHoldStore, notifier: BookingNotifier
    ) -> None:
        self.session = session
        self.holds = holds
        self.notifier = notifier
        self.bookings = BookingRepository(session)
        self.listings = ListingRepository(session)
        self.slots = SlotRepository(session)

    # --- buyer ----------------------------------------------------------------------------

    async def create(self, buyer: User, data: BookingCreate) -> BookingResponse:
        # 1. The buyer must hold the slot. This is what makes the 5-minute reservation mean
        #    something: without a hold, nobody can book.
        if await self.holds.holder(data.listing_id, data.slot_start) != buyer.id:
            raise AppError(
                "hold_required",
                "Your hold on this slot has expired or doesn't exist. Select the slot again.",
                409,
            )

        listing = await self.listings.get(data.listing_id)
        if listing is None:
            raise AppError("not_found", "Listing not found", 404)
        if listing.status is not ListingStatus.ACTIVE:
            raise AppError("listing_unavailable", "This listing is not taking visits", 409)
        slot = await self.slots.get(listing.id, data.slot_start)
        if slot is None:
            raise AppError("slot_not_found", "No such slot for this listing", 404)
        if slot.slot_start <= datetime.now(UTC):
            raise AppError("slot_in_past", "This slot has already started", 409)

        # 2. Insert. The partial unique index is the final word: if a hold lapsed and two
        #    buyers both got this far, Postgres accepts exactly one of them.
        try:
            booking = await self.bookings.create(listing.id, buyer.id, slot.slot_start, data.note)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            if ACTIVE_BOOKING_INDEX in str(exc.orig):
                raise AppError(
                    "slot_booked", "This slot has just been booked by someone else", 409
                ) from exc
            raise

        # 3. The hold has done its job. Compare-and-delete, so we only remove our own.
        await self.holds.release(listing.id, slot.slot_start, buyer.id)
        logger.info("booking_created", booking_id=booking.id, listing_id=listing.id)

        # 4. Tell the agent live and queue both emails; never fails the request.
        saved = await self._load(booking.id)
        await self.notifier.booking_created(saved)
        return BookingResponse.model_validate(saved)

    async def list_mine(self, buyer: User) -> list[BookingResponse]:
        bookings = await self.bookings.list_for_buyer(buyer.id)
        return [BookingResponse.model_validate(b) for b in bookings]

    async def cancel(self, buyer: User, booking_id: int) -> BookingResponse:
        booking = await self.bookings.get_detailed(booking_id)
        # 404 rather than 403 for someone else's booking: bookings are private, so we don't
        # confirm that the ID exists.
        if booking is None or booking.buyer_id != buyer.id:
            raise AppError("not_found", "Booking not found", 404)
        if booking.slot_start <= datetime.now(UTC):
            raise AppError("visit_started", "Past visits can't be cancelled", 409)

        changed = await self.bookings.transition(
            booking.id, ACTIVE_BOOKING_STATUSES, BookingStatus.CANCELLED
        )
        if not changed:
            raise AppError(
                "invalid_status", f"A {booking.status.value} booking can't be cancelled", 409
            )
        await self.session.commit()
        logger.info("booking_cancelled", booking_id=booking.id)
        saved = await self._load(booking.id)
        await self.notifier.booking_cancelled(saved)
        return BookingResponse.model_validate(saved)

    # --- agent ----------------------------------------------------------------------------

    async def list_for_agent(
        self, agent: User, status: BookingStatus | None, page: int, page_size: int
    ) -> AgentBookingPage:
        bookings, total = await self.bookings.list_for_agent(agent.id, status, page, page_size)
        return AgentBookingPage(
            items=[AgentBookingResponse.model_validate(b) for b in bookings],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def stats(self, agent: User) -> AgentStats:
        return AgentStats(
            active_listings=await self.listings.count_for_agent(agent.id, ListingStatus.ACTIVE),
            pending_requests=await self.bookings.count_for_agent(agent.id, BookingStatus.PENDING),
            upcoming_visits=await self.bookings.count_for_agent(
                agent.id, BookingStatus.ACCEPTED, after=datetime.now(UTC)
            ),
        )

    async def decide(
        self, agent: User, booking_id: int, data: AgentBookingDecision
    ) -> AgentBookingResponse:
        booking = await self.bookings.get_detailed(booking_id)
        if booking is None or booking.listing.agent_id != agent.id:
            raise AppError("not_found", "Booking not found", 404)

        changed = await self.bookings.transition(booking.id, [BookingStatus.PENDING], data.status)
        if not changed:
            # Most likely the buyer cancelled a moment ago.
            current = (await self._load(booking.id)).status.value
            raise AppError(
                "invalid_status",
                f"Only pending bookings can be updated (this one is {current})",
                409,
            )
        await self.session.commit()
        logger.info("booking_decided", booking_id=booking.id, status=data.status.value)
        return AgentBookingResponse.model_validate(await self._load(booking.id))

    async def _load(self, booking_id: int) -> Booking:
        booking = await self.bookings.get_detailed(booking_id)
        if booking is None:  # pragma: no cover - we just wrote it
            raise AppError("not_found", "Booking not found", 404)
        return booking
