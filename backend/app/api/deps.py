"""Builds request-scoped services from the shared session, Redis client and settings."""

from typing import Annotated

from fastapi import Depends

from app.core.config import get_settings
from app.core.dependencies import DbSession, RedisClient
from app.services.bookings import BookingService
from app.services.image_storage import get_image_storage
from app.services.listings import ListingService
from app.services.search_cache import SearchCache
from app.services.slot_holds import SlotHoldStore
from app.services.slots import SlotService


def get_listing_service(session: DbSession, redis: RedisClient) -> ListingService:
    settings = get_settings()
    cache = SearchCache(redis, settings.cache_enabled, settings.search_cache_ttl_seconds)
    return ListingService(session, cache, get_image_storage())


def get_hold_store(redis: RedisClient) -> SlotHoldStore:
    return SlotHoldStore(redis, get_settings().slot_hold_seconds)


HoldStoreDep = Annotated[SlotHoldStore, Depends(get_hold_store)]


def get_slot_service(session: DbSession, holds: HoldStoreDep) -> SlotService:
    return SlotService(session, holds)


def get_booking_service(session: DbSession, holds: HoldStoreDep) -> BookingService:
    return BookingService(session, holds)


ListingServiceDep = Annotated[ListingService, Depends(get_listing_service)]
SlotServiceDep = Annotated[SlotService, Depends(get_slot_service)]
BookingServiceDep = Annotated[BookingService, Depends(get_booking_service)]
