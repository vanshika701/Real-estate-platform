from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.listing import Listing


class AvailabilitySlot(Base):
    __tablename__ = "availability_slots"
    __table_args__ = (
        UniqueConstraint("listing_id", "slot_start"),
        CheckConstraint("slot_end > slot_start", name="end_after_start"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # The (listing_id, slot_start) unique constraint's index also serves listing_id lookups.
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"))
    slot_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    slot_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    listing: Mapped["Listing"] = relationship(back_populates="slots")
