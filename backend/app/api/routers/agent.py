from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import ListingServiceDep
from app.core.dependencies import AgentUser
from app.schemas.listings import MAX_PAGE_SIZE, ListingPage

router = APIRouter(prefix="/agent", tags=["agent"])


@router.get("/listings", response_model=ListingPage)
async def my_listings(
    agent: AgentUser,
    service: ListingServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 20,
) -> ListingPage:
    """The agent's own listings in every status, for the management screen."""
    return await service.list_for_agent(agent, page, page_size)
