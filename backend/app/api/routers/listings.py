from typing import Annotated

from fastapi import APIRouter, File, Query, Response, UploadFile, status

from app.api.deps import ListingServiceDep
from app.core.dependencies import AgentUser
from app.schemas.listings import (
    ListingCreate,
    ListingDetail,
    ListingFilters,
    ListingImageResponse,
    ListingPage,
    ListingUpdate,
)

router = APIRouter(prefix="/listings", tags=["listings"])


@router.get("", response_model=ListingPage)
async def search_listings(
    filters: Annotated[ListingFilters, Query()],
    service: ListingServiceDep,
    response: Response,
) -> ListingPage:
    page, cache_hit = await service.search(filters)
    # Lets the load test (and anyone debugging) see whether the cache served the request.
    response.headers["X-Cache"] = "HIT" if cache_hit else "MISS"
    return page


@router.get("/{listing_id}", response_model=ListingDetail)
async def get_listing(listing_id: int, service: ListingServiceDep) -> ListingDetail:
    return await service.get_detail(listing_id)


@router.post("", response_model=ListingDetail, status_code=status.HTTP_201_CREATED)
async def create_listing(
    data: ListingCreate, agent: AgentUser, service: ListingServiceDep
) -> ListingDetail:
    return await service.create(agent, data)


@router.patch("/{listing_id}", response_model=ListingDetail)
async def update_listing(
    listing_id: int, data: ListingUpdate, agent: AgentUser, service: ListingServiceDep
) -> ListingDetail:
    return await service.update(agent, listing_id, data)


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_listing(listing_id: int, agent: AgentUser, service: ListingServiceDep) -> None:
    await service.delete(agent, listing_id)


@router.post(
    "/{listing_id}/images",
    response_model=ListingImageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_listing_image(
    listing_id: int,
    agent: AgentUser,
    service: ListingServiceDep,
    file: Annotated[UploadFile, File(description="JPEG, PNG or WebP, max 5 MB")],
) -> ListingImageResponse:
    return await service.add_image(agent, listing_id, file)


@router.delete("/{listing_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_listing_image(
    listing_id: int, image_id: int, agent: AgentUser, service: ListingServiceDep
) -> None:
    await service.delete_image(agent, listing_id, image_id)
