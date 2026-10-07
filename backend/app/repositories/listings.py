from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models import Listing, ListingImage, ListingStatus
from app.schemas.listings import ListingFilters, ListingSort

# Correlated subquery for the first image, so a search page is one query
# instead of loading every image for every listing.
_cover_image_url = (
    select(ListingImage.url)
    .where(ListingImage.listing_id == Listing.id)
    .order_by(ListingImage.position, ListingImage.id)
    .limit(1)
    .correlate(Listing)
    .scalar_subquery()
    .label("cover_image_url")
)

_ORDERING: dict[ListingSort, tuple[ColumnElement[Any], ...]] = {
    # id as a tie-breaker gives a stable order, so rows can't shift between pages.
    ListingSort.PRICE_ASC: (Listing.price.asc(), Listing.id.asc()),
    ListingSort.PRICE_DESC: (Listing.price.desc(), Listing.id.desc()),
    ListingSort.NEWEST: (Listing.created_at.desc(), Listing.id.desc()),
}


class ListingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _search_conditions(filters: ListingFilters) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = [Listing.status == ListingStatus.ACTIVE]
        if filters.city:
            conditions.append(func.lower(Listing.city) == filters.city.lower())
        if filters.min_price is not None:
            conditions.append(Listing.price >= filters.min_price)
        if filters.max_price is not None:
            conditions.append(Listing.price <= filters.max_price)
        if filters.bhk is not None:
            conditions.append(Listing.bhk == filters.bhk)
        if filters.property_type is not None:
            conditions.append(Listing.property_type == filters.property_type)
        return conditions

    async def _page(
        self,
        conditions: Sequence[ColumnElement[bool]],
        ordering: tuple[ColumnElement[Any], ...],
        page: int,
        page_size: int,
    ) -> tuple[list[tuple[Listing, str | None]], int]:
        total = await self.session.scalar(
            select(func.count()).select_from(Listing).where(*conditions)
        )
        query: Select[tuple[Listing, str | None]] = (
            select(Listing, _cover_image_url)
            .where(*conditions)
            .order_by(*ordering)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self.session.execute(query)).all()
        return [(listing, cover) for listing, cover in rows], total or 0

    async def search(self, filters: ListingFilters) -> tuple[list[tuple[Listing, str | None]], int]:
        return await self._page(
            self._search_conditions(filters),
            _ORDERING[filters.sort],
            filters.page,
            filters.page_size,
        )

    async def list_for_agent(
        self, agent_id: int, page: int, page_size: int
    ) -> tuple[list[tuple[Listing, str | None]], int]:
        return await self._page(
            [Listing.agent_id == agent_id],
            _ORDERING[ListingSort.NEWEST],
            page,
            page_size,
        )

    async def count_for_agent(self, agent_id: int, status: ListingStatus) -> int:
        count = await self.session.scalar(
            select(func.count()).where(Listing.agent_id == agent_id, Listing.status == status)
        )
        return count or 0

    async def get(self, listing_id: int) -> Listing | None:
        return await self.session.get(Listing, listing_id)

    async def get_detail(self, listing_id: int) -> Listing | None:
        query = (
            select(Listing)
            .where(Listing.id == listing_id)
            .options(selectinload(Listing.images), joinedload(Listing.agent))
            # Refresh relationships even if this Listing is already in the session's identity map.
            .execution_options(populate_existing=True)
        )
        return await self.session.scalar(query)

    async def create(self, agent_id: int, values: dict[str, Any]) -> Listing:
        listing = Listing(agent_id=agent_id, **values)
        self.session.add(listing)
        await self.session.flush()
        return listing

    async def update(self, listing: Listing, values: dict[str, Any]) -> None:
        for field, value in values.items():
            setattr(listing, field, value)
        await self.session.flush()

    async def delete(self, listing: Listing) -> None:
        # Images, slots and bookings go with it via ON DELETE CASCADE (passive_deletes).
        await self.session.delete(listing)
        await self.session.flush()

    async def image_urls(self, listing_id: int) -> list[str]:
        rows = await self.session.scalars(
            select(ListingImage.url).where(ListingImage.listing_id == listing_id)
        )
        return list(rows)

    async def count_images(self, listing_id: int) -> int:
        count = await self.session.scalar(
            select(func.count()).where(ListingImage.listing_id == listing_id)
        )
        return count or 0

    async def next_image_position(self, listing_id: int) -> int:
        current = await self.session.scalar(
            select(func.max(ListingImage.position)).where(ListingImage.listing_id == listing_id)
        )
        return 0 if current is None else current + 1

    async def add_image(self, listing_id: int, url: str, position: int) -> ListingImage:
        image = ListingImage(listing_id=listing_id, url=url, position=position)
        self.session.add(image)
        await self.session.flush()
        return image

    async def get_image(self, listing_id: int, image_id: int) -> ListingImage | None:
        return await self.session.scalar(
            select(ListingImage).where(
                ListingImage.id == image_id, ListingImage.listing_id == listing_id
            )
        )

    async def delete_image(self, image: ListingImage) -> None:
        await self.session.delete(image)
        await self.session.flush()
