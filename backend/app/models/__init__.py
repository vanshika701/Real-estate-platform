"""Importing this package registers every model on Base.metadata (needed by Alembic)."""

from app.models.base import Base
from app.models.booking import ACTIVE_BOOKING_STATUSES, Booking, BookingStatus
from app.models.listing import Listing, ListingImage, ListingStatus, PropertyType
from app.models.slot import AvailabilitySlot
from app.models.user import User, UserRole

__all__ = [
    "ACTIVE_BOOKING_STATUSES",
    "AvailabilitySlot",
    "Base",
    "Booking",
    "BookingStatus",
    "Listing",
    "ListingImage",
    "ListingStatus",
    "PropertyType",
    "User",
    "UserRole",
]
