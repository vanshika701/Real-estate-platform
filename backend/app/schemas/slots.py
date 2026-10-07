from datetime import datetime, timedelta
from enum import StrEnum
from itertools import pairwise
from typing import Self

from pydantic import AwareDatetime, BaseModel, Field, model_validator

MIN_SLOT = timedelta(minutes=15)
MAX_SLOT = timedelta(hours=4)
MAX_SLOTS_PER_REQUEST = 100


class SlotStatus(StrEnum):
    AVAILABLE = "available"
    HELD = "held"
    BOOKED = "booked"


class SlotInput(BaseModel):
    # AwareDatetime rejects timestamps without a timezone, which would be ambiguous.
    slot_start: AwareDatetime
    slot_end: AwareDatetime

    @model_validator(mode="after")
    def _check_duration(self) -> Self:
        duration = self.slot_end - self.slot_start
        if not MIN_SLOT <= duration <= MAX_SLOT:
            raise ValueError("a slot must last between 15 minutes and 4 hours")
        return self


class SlotCreateRequest(BaseModel):
    slots: list[SlotInput] = Field(min_length=1, max_length=MAX_SLOTS_PER_REQUEST)

    @model_validator(mode="after")
    def _no_overlaps_within_request(self) -> Self:
        ordered = sorted(self.slots, key=lambda s: s.slot_start)
        for previous, current in pairwise(ordered):
            if current.slot_start < previous.slot_end:
                raise ValueError(f"slots overlap at {current.slot_start.isoformat()}")
        return self


class SlotResponse(BaseModel):
    id: int
    slot_start: datetime
    slot_end: datetime
    status: SlotStatus


class HoldRequest(BaseModel):
    slot_start: AwareDatetime


class HoldResponse(BaseModel):
    listing_id: int
    slot_start: datetime
    expires_at: datetime
    expires_in: int = Field(description="Seconds until the hold lapses")
