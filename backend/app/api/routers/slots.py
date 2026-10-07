from fastapi import APIRouter, status

from app.api.deps import SlotServiceDep
from app.core.dependencies import AgentUser, BuyerUser
from app.schemas.slots import HoldRequest, HoldResponse, SlotCreateRequest, SlotResponse

router = APIRouter(prefix="/listings/{listing_id}/slots", tags=["slots"])


@router.post("", response_model=list[SlotResponse], status_code=status.HTTP_201_CREATED)
async def create_slots(
    listing_id: int, data: SlotCreateRequest, agent: AgentUser, service: SlotServiceDep
) -> list[SlotResponse]:
    return await service.create_slots(agent, listing_id, data)


@router.get("", response_model=list[SlotResponse])
async def list_slots(listing_id: int, service: SlotServiceDep) -> list[SlotResponse]:
    """Upcoming slots (next 30 days), each marked available, held or booked."""
    return await service.list_slots(listing_id)


@router.post("/hold", response_model=HoldResponse)
async def hold_slot(
    listing_id: int, data: HoldRequest, buyer: BuyerUser, service: SlotServiceDep
) -> HoldResponse:
    """Reserve a slot for 5 minutes while the buyer confirms the booking."""
    return await service.hold(buyer, listing_id, data.slot_start)


@router.delete("/hold", status_code=status.HTTP_204_NO_CONTENT)
async def release_hold(
    listing_id: int, data: HoldRequest, buyer: BuyerUser, service: SlotServiceDep
) -> None:
    """Give up a hold early, e.g. when the buyer picks a different slot."""
    await service.release_hold(buyer, listing_id, data.slot_start)
