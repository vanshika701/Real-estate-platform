from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import BookingServiceDep, ListingServiceDep
from app.core.dependencies import AgentUser
from app.models import BookingStatus
from app.schemas.bookings import (
    AgentBookingDecision,
    AgentBookingPage,
    AgentBookingResponse,
    AgentStats,
)
from app.schemas.listings import MAX_PAGE_SIZE, ListingPage

router = APIRouter(prefix="/agent", tags=["agent"])

Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)]


@router.get("/listings", response_model=ListingPage)
async def my_listings(
    agent: AgentUser, service: ListingServiceDep, page: Page = 1, page_size: PageSize = 20
) -> ListingPage:
    """The agent's own listings in every status, for the management screen."""
    return await service.list_for_agent(agent, page, page_size)


@router.get("/bookings", response_model=AgentBookingPage)
async def bookings_for_my_listings(
    agent: AgentUser,
    service: BookingServiceDep,
    status: BookingStatus | None = None,
    page: Page = 1,
    page_size: PageSize = 20,
) -> AgentBookingPage:
    """Visit requests across the agent's listings, soonest first."""
    return await service.list_for_agent(agent, status, page, page_size)


@router.patch("/bookings/{booking_id}", response_model=AgentBookingResponse)
async def decide_booking(
    booking_id: int, data: AgentBookingDecision, agent: AgentUser, service: BookingServiceDep
) -> AgentBookingResponse:
    """Accept or reject a pending visit request."""
    return await service.decide(agent, booking_id, data)


@router.get("/stats", response_model=AgentStats)
async def dashboard_stats(agent: AgentUser, service: BookingServiceDep) -> AgentStats:
    """Headline numbers for the agent dashboard."""
    return await service.stats(agent)
