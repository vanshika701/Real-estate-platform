from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, enum_check, str_enum

if TYPE_CHECKING:
    from app.models.listing import Listing
    from app.models.user import User


class BookingStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


# Statuses that occupy a slot. Rejected/cancelled bookings free it for someone else.
ACTIVE_BOOKING_STATUSES = (BookingStatus.PENDING, BookingStatus.ACCEPTED)


class Booking(TimestampMixin, Base):
    __tablename__ = "bookings"
    __table_args__ = (
        enum_check("status", BookingStatus),
        # The final guarantee against double-booking: even if two requests slip past the Redis
        # hold, Postgres rejects the second active booking for the same listing and slot.
        Index(
            "uq_bookings_active_slot",
            "listing_id",
            "slot_start",
            unique=True,
            postgresql_where=text("status IN ('pending', 'accepted')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    slot_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[BookingStatus] = mapped_column(
        str_enum(BookingStatus),
        default=BookingStatus.PENDING,
        server_default=BookingStatus.PENDING.value,
    )
    note: Mapped[str | None] = mapped_column(String(500))

    listing: Mapped["Listing"] = relationship()
    buyer: Mapped["User"] = relationship()
