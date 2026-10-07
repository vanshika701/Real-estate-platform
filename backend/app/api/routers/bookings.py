from fastapi import APIRouter, status

from app.api.deps import BookingServiceDep
from app.core.dependencies import BuyerUser
from app.schemas.bookings import BookingCreate, BookingResponse

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    data: BookingCreate, buyer: BuyerUser, service: BookingServiceDep
) -> BookingResponse:
    """Confirm a slot the buyer currently holds."""
    return await service.create(buyer, data)


@router.get("/me", response_model=list[BookingResponse])
async def my_bookings(buyer: BuyerUser, service: BookingServiceDep) -> list[BookingResponse]:
    return await service.list_mine(buyer)


@router.patch("/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking(
    booking_id: int, buyer: BuyerUser, service: BookingServiceDep
) -> BookingResponse:
    return await service.cancel(buyer, booking_id)
