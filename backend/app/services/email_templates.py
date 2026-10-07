from datetime import datetime, timedelta, timezone
from html import escape

from app.core.config import get_settings
from app.models import Booking
from app.services.email import EmailMessage

# Visits happen in India; India has no DST, so a fixed +05:30 offset is exact.
IST = timezone(timedelta(hours=5, minutes=30))


def _when(slot_start: datetime) -> str:
    return slot_start.astimezone(IST).strftime("%A, %d %B %Y at %I:%M %p IST")


def _html(paragraphs: list[str], link_text: str, link_url: str) -> str:
    body = "".join(f"<p>{escape(p)}</p>" for p in paragraphs)
    return f'{body}<p><a href="{escape(link_url)}">{escape(link_text)}</a></p>'


def booking_request_for_buyer(booking: Booking) -> EmailMessage:
    """Sent to the buyer right after they book: the request is in, pending the agent's reply."""
    listing = booking.listing
    url = f"{get_settings().app_url}/my-bookings"
    paragraphs = [
        f"Hi {booking.buyer.full_name},",
        f"Your site visit request for {listing.title} has been sent to the agent.",
        f"When: {_when(booking.slot_start)}",
        f"Where: {listing.address}",
        "You'll get an update once the agent accepts or declines.",
    ]
    return EmailMessage(
        to=booking.buyer.email,
        subject=f"Visit requested: {listing.title}",
        text="\n\n".join([*paragraphs, f"View your bookings: {url}"]),
        html=_html(paragraphs, "View your bookings", url),
    )


def new_booking_for_agent(booking: Booking) -> EmailMessage:
    listing = booking.listing
    buyer = booking.buyer
    url = f"{get_settings().app_url}/agent/dashboard"
    paragraphs = [
        f"Hi {listing.agent.full_name},",
        f"{buyer.full_name} has requested a site visit for {listing.title}.",
        f"When: {_when(booking.slot_start)}",
        f"Buyer contact: {buyer.email}" + (f", {buyer.phone}" if buyer.phone else ""),
    ]
    if booking.note:
        paragraphs.append(f"Note from the buyer: {booking.note}")
    return EmailMessage(
        to=listing.agent.email,
        subject=f"New visit request: {listing.title}",
        text="\n\n".join([*paragraphs, f"Review it on your dashboard: {url}"]),
        html=_html(paragraphs, "Review it on your dashboard", url),
    )
