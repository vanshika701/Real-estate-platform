import uuid

import structlog
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import Listing, User
from app.repositories.listings import ListingRepository
from app.schemas.listings import (
    ListingCreate,
    ListingDetail,
    ListingFilters,
    ListingImageResponse,
    ListingPage,
    ListingSummary,
    ListingUpdate,
)
from app.services.image_storage import ImageStorage
from app.services.image_validation import detect_image_type
from app.services.search_cache import SearchCache

logger = structlog.get_logger(__name__)

_SUMMARY_COLUMNS = [name for name in ListingSummary.model_fields if name != "cover_image_url"]


def _summaries(rows: list[tuple[Listing, str | None]]) -> list[ListingSummary]:
    return [
        ListingSummary.model_validate(
            {
                **{name: getattr(listing, name) for name in _SUMMARY_COLUMNS},
                "cover_image_url": cover,
            }
        )
        for listing, cover in rows
    ]


class ListingService:
    def __init__(self, session: AsyncSession, cache: SearchCache, storage: ImageStorage) -> None:
        self.session = session
        self.listings = ListingRepository(session)
        self.cache = cache
        self.storage = storage

    # --- public reads ---------------------------------------------------------------------

    async def search(self, filters: ListingFilters) -> tuple[ListingPage, bool]:
        """Return the page and whether it came from the cache."""
        cached = await self.cache.get(filters)
        if cached is not None:
            return cached, True

        rows, total = await self.listings.search(filters)
        page = ListingPage(
            items=_summaries(rows), total=total, page=filters.page, page_size=filters.page_size
        )
        await self.cache.set(filters, page)
        return page, False

    async def get_detail(self, listing_id: int) -> ListingDetail:
        listing = await self.listings.get_detail(listing_id)
        if listing is None:
            raise AppError("not_found", "Listing not found", 404)
        return ListingDetail.model_validate(listing)

    # --- agent writes ---------------------------------------------------------------------

    async def list_for_agent(self, agent: User, page: int, page_size: int) -> ListingPage:
        rows, total = await self.listings.list_for_agent(agent.id, page, page_size)
        return ListingPage(items=_summaries(rows), total=total, page=page, page_size=page_size)

    async def create(self, agent: User, data: ListingCreate) -> ListingDetail:
        listing = await self.listings.create(agent.id, data.model_dump())
        await self.session.commit()
        await self.cache.invalidate_all()
        logger.info("listing_created", listing_id=listing.id, agent_id=agent.id)
        return await self.get_detail(listing.id)

    async def update(self, agent: User, listing_id: int, data: ListingUpdate) -> ListingDetail:
        listing = await self._get_owned(agent, listing_id)
        await self.listings.update(listing, data.model_dump(exclude_unset=True))
        await self.session.commit()
        await self.cache.invalidate_all()
        return await self.get_detail(listing.id)

    async def delete(self, agent: User, listing_id: int) -> None:
        listing = await self._get_owned(agent, listing_id)
        image_urls = await self.listings.image_urls(listing.id)
        await self.listings.delete(listing)
        await self.session.commit()
        await self.cache.invalidate_all()
        # Files go only after the DB commit succeeds; a failure here just leaves an orphan file.
        for url in image_urls:
            await self._delete_file_quietly(url)
        logger.info("listing_deleted", listing_id=listing_id, agent_id=agent.id)

    async def add_image(
        self, agent: User, listing_id: int, upload: UploadFile
    ) -> ListingImageResponse:
        settings = get_settings()
        listing = await self._get_owned(agent, listing_id)
        if await self.listings.count_images(listing.id) >= settings.max_images_per_listing:
            raise AppError(
                "too_many_images",
                f"A listing can have at most {settings.max_images_per_listing} images",
                409,
            )

        # Read one byte past the limit: enough to know it's too big without reading it all.
        data = await upload.read(settings.max_image_bytes + 1)
        if len(data) > settings.max_image_bytes:
            limit_mb = settings.max_image_bytes // (1024 * 1024)
            raise AppError("file_too_large", f"Images must be at most {limit_mb} MB", 413)
        content_type, extension = detect_image_type(data)

        # A random name: never trust or reuse the client's filename.
        key = f"listings/{listing.id}/{uuid.uuid4().hex}.{extension}"
        url = await self.storage.save(key, data, content_type)
        try:
            position = await self.listings.next_image_position(listing.id)
            image = await self.listings.add_image(listing.id, url, position)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            await self._delete_file_quietly(url)  # don't leave a file with no DB row
            raise

        await self.cache.invalidate_all()  # the cover image in search results may have changed
        return ListingImageResponse.model_validate(image)

    async def delete_image(self, agent: User, listing_id: int, image_id: int) -> None:
        listing = await self._get_owned(agent, listing_id)
        image = await self.listings.get_image(listing.id, image_id)
        if image is None:
            raise AppError("not_found", "Image not found", 404)
        url = image.url
        await self.listings.delete_image(image)
        await self.session.commit()
        await self.cache.invalidate_all()
        await self._delete_file_quietly(url)

    # --- helpers --------------------------------------------------------------------------

    async def _get_owned(self, agent: User, listing_id: int) -> Listing:
        listing = await self.listings.get(listing_id)
        if listing is None:
            raise AppError("not_found", "Listing not found", 404)
        if listing.agent_id != agent.id:
            # 403 rather than 404: listings are public, so hiding existence protects nothing.
            raise AppError("forbidden", "You can only modify your own listings", 403)
        return listing

    async def _delete_file_quietly(self, url: str) -> None:
        try:
            await self.storage.delete(url)
        except Exception:
            logger.warning("image_delete_failed", url=url, exc_info=True)
