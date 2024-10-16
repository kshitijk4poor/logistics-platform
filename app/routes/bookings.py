from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, rate_limit, get_db
from app.models import User
from app.schemas.booking import BookingRequest, BookingResponse
from app.services.booking.booking_service import create_new_booking

router = APIRouter()

@router.post("/book", response_model=BookingResponse)
@rate_limit(max_calls=5, time_frame=60)
async def create_booking(
    booking_data: BookingRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_new_booking(booking_data, current_user, db, background_tasks)
