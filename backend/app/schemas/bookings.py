from datetime import datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

from app.models import BookingStatus


class BookingCreate(BaseModel):
    listing_id: int
    slot_start: AwareDatetime
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None


class AgentBookingDecision(BaseModel):
    status: Literal[BookingStatus.ACCEPTED, BookingStatus.REJECTED]


class BookingListing(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    city: str
    locality: str
    address: str


class BuyerContact(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone: str | None


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_id: int
    slot_start: datetime
    status: BookingStatus
    note: str | None
    created_at: datetime
    listing: BookingListing


class AgentBookingResponse(BookingResponse):
    buyer: BuyerContact


class AgentStats(BaseModel):
    active_listings: int
    pending_requests: int
    upcoming_visits: int = Field(description="Accepted visits that haven't happened yet")


class AgentBookingPage(BaseModel):
    items: list[AgentBookingResponse]
    total: int
    page: int
    page_size: int = Field(le=50)
