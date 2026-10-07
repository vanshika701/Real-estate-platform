from datetime import datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models import ListingStatus, PropertyType

MAX_PAGE_SIZE = 50
MAX_PRICE = 10_000_000_000  # ₹1,000 crore: well above any real listing, blocks absurd values

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ListingSort(StrEnum):
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    NEWEST = "newest"


class ListingFilters(BaseModel):
    """Query parameters for GET /listings."""

    city: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    min_price: int | None = Field(default=None, ge=0)
    max_price: int | None = Field(default=None, ge=0)
    bhk: int | None = Field(default=None, ge=0, le=20)
    property_type: PropertyType | None = None
    sort: ListingSort = ListingSort.NEWEST
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=12, ge=1, le=MAX_PAGE_SIZE)

    @model_validator(mode="after")
    def _check_price_range(self) -> Self:
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price must not exceed max_price")
        return self

    def cache_identity(self) -> dict[str, object]:
        """Canonical form for cache keys: equivalent queries must produce the same key."""
        data = self.model_dump(mode="json", exclude_none=True)
        if self.city:
            data["city"] = self.city.lower()
        else:
            data.pop("city", None)  # "" and absent mean the same thing
        return data


class ListingCreate(BaseModel):
    title: Annotated[Text, StringConstraints(min_length=5, max_length=200)]
    description: Annotated[Text, StringConstraints(min_length=10, max_length=5000)]
    city: Annotated[Text, StringConstraints(max_length=100)]
    locality: Annotated[Text, StringConstraints(max_length=100)]
    address: Annotated[Text, StringConstraints(max_length=300)]
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    price: int = Field(gt=0, le=MAX_PRICE)
    bhk: int = Field(ge=0, le=20)
    area_sqft: int = Field(gt=0, le=1_000_000)
    property_type: PropertyType
    status: ListingStatus = ListingStatus.ACTIVE


class ListingUpdate(BaseModel):
    """Partial update: only fields present in the request body are changed."""

    title: Annotated[Text, StringConstraints(min_length=5, max_length=200)] | None = None
    description: Annotated[Text, StringConstraints(min_length=10, max_length=5000)] | None = None
    city: Annotated[Text, StringConstraints(max_length=100)] | None = None
    locality: Annotated[Text, StringConstraints(max_length=100)] | None = None
    address: Annotated[Text, StringConstraints(max_length=300)] | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    price: int | None = Field(default=None, gt=0, le=MAX_PRICE)
    bhk: int | None = Field(default=None, ge=0, le=20)
    area_sqft: int | None = Field(default=None, gt=0, le=1_000_000)
    property_type: PropertyType | None = None
    status: ListingStatus | None = None

    @model_validator(mode="after")
    def _reject_explicit_nulls(self) -> Self:
        # Omitting a field means "leave unchanged"; sending null for a required column is an error.
        nulls = sorted(name for name in self.model_fields_set if getattr(self, name) is None)
        if nulls:
            raise ValueError(f"fields cannot be null: {', '.join(nulls)}")
        return self


class ListingImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    position: int


class AgentContact(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone: str | None


class ListingSummary(BaseModel):
    """Card / map-pin view used in search results."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    city: str
    locality: str
    latitude: float
    longitude: float
    price: int
    bhk: int
    area_sqft: int
    property_type: PropertyType
    status: ListingStatus
    cover_image_url: str | None
    created_at: datetime


class ListingDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: int
    title: str
    description: str
    city: str
    locality: str
    address: str
    latitude: float
    longitude: float
    price: int
    bhk: int
    area_sqft: int
    property_type: PropertyType
    status: ListingStatus
    created_at: datetime
    updated_at: datetime
    images: list[ListingImageResponse]
    agent: AgentContact


class ListingPage(BaseModel):
    items: list[ListingSummary]
    total: int
    page: int
    page_size: int
