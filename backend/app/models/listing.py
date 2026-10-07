from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, enum_check, str_enum

if TYPE_CHECKING:
    from app.models.slot import AvailabilitySlot
    from app.models.user import User


class PropertyType(StrEnum):
    APARTMENT = "apartment"
    VILLA = "villa"
    PLOT = "plot"
    INDEPENDENT_HOUSE = "independent_house"


class ListingStatus(StrEnum):
    ACTIVE = "active"
    SOLD = "sold"
    INACTIVE = "inactive"


class Listing(TimestampMixin, Base):
    __tablename__ = "listings"
    __table_args__ = (
        enum_check("property_type", PropertyType),
        enum_check("status", ListingStatus),
        CheckConstraint("price > 0", name="price_positive"),
        CheckConstraint("bhk >= 0", name="bhk_non_negative"),  # plots have 0 BHK
        CheckConstraint("area_sqft > 0", name="area_positive"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude_range"),
        # City search is case-insensitive (WHERE lower(city) = ...), so the index must be on
        # lower(city); a plain index on city could not serve that query.
        Index("ix_listings_city_lower", text("lower(city)")),
    )
    # Fetch server-side values (updated_at, created_at) via RETURNING on every write; otherwise
    # reading them after an update would trigger a lazy load, which async SQLAlchemy forbids.
    __mapper_args__ = {"eager_defaults": True}  # noqa: RUF012 - SQLAlchemy's declared API

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(100))
    locality: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(300))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    # INR as a whole number: no float rounding, and BIGINT because premium homes exceed INT's
    # ~₹214 crore ceiling.
    price: Mapped[int] = mapped_column(BigInteger, index=True)
    bhk: Mapped[int] = mapped_column(Integer, index=True)
    area_sqft: Mapped[int] = mapped_column(Integer)
    property_type: Mapped[PropertyType] = mapped_column(str_enum(PropertyType))
    status: Mapped[ListingStatus] = mapped_column(
        str_enum(ListingStatus),
        default=ListingStatus.ACTIVE,
        server_default=ListingStatus.ACTIVE.value,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    agent: Mapped["User"] = relationship(back_populates="listings")
    images: Mapped[list["ListingImage"]] = relationship(
        back_populates="listing",
        order_by="ListingImage.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    slots: Mapped[list["AvailabilitySlot"]] = relationship(
        back_populates="listing", cascade="all, delete-orphan", passive_deletes=True
    )


class ListingImage(Base):
    __tablename__ = "listing_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(Integer, default=0)

    listing: Mapped[Listing] = relationship(back_populates="images")
