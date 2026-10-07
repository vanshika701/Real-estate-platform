"""Builds request-scoped services from the shared session, Redis client and settings."""

from typing import Annotated

from fastapi import Depends

from app.core.config import get_settings
from app.core.dependencies import DbSession, RedisClient
from app.services.image_storage import get_image_storage
from app.services.listings import ListingService
from app.services.search_cache import SearchCache


def get_listing_service(session: DbSession, redis: RedisClient) -> ListingService:
    settings = get_settings()
    cache = SearchCache(redis, settings.cache_enabled, settings.search_cache_ttl_seconds)
    return ListingService(session, cache, get_image_storage())


ListingServiceDep = Annotated[ListingService, Depends(get_listing_service)]
