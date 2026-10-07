import structlog

from app.models import Booking
from app.schemas.bookings import AgentBookingResponse
from app.services.agent_events import AgentEventPublisher
from app.services.email_queue import EmailQueue
from app.services.email_templates import booking_request_for_buyer, new_booking_for_agent

logger = structlog.get_logger(__name__)


class BookingNotifier:
    """Side effects after a booking change: live agent events and queued emails.

    These run after the DB commit and never raise. The booking is already saved, so a Redis
    hiccup here must not turn a successful booking into an error response. The trade-off is
    that a notification can be lost if Redis is down at that moment; a transactional outbox
    table would close that gap.
    """

    def __init__(self, emails: EmailQueue, events: AgentEventPublisher) -> None:
        self.emails = emails
        self.events = events

    async def booking_created(self, booking: Booking) -> None:
        await self._publish(booking, "booking.created")
        for message in (booking_request_for_buyer(booking), new_booking_for_agent(booking)):
            try:
                await self.emails.enqueue(message)
            except Exception:
                logger.exception("email_enqueue_failed", booking_id=booking.id)

    async def booking_cancelled(self, booking: Booking) -> None:
        await self._publish(booking, "booking.cancelled")

    async def _publish(self, booking: Booking, event_type: str) -> None:
        payload = AgentBookingResponse.model_validate(booking).model_dump(mode="json")
        try:
            await self.events.publish(booking.listing.agent_id, event_type, {"booking": payload})
        except Exception:
            logger.exception("agent_event_publish_failed", booking_id=booking.id)
