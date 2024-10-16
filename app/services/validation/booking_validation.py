from app.schemas.booking import BookingRequest
from app.services.validation.validation import (
    is_overlapping_booking,
    is_under_maintenance,
)
from sqlalchemy.ext.asyncio import AsyncSession


async def validate_booking(db: AsyncSession, booking_data: BookingRequest):
    vehicle_id = booking_data.vehicle_type
    scheduled_time = booking_data.scheduled_time

    if await is_under_maintenance(db, vehicle_id, scheduled_time):
        raise ValueError("Vehicle is under maintenance at the scheduled time.")

    if await is_overlapping_booking(db, vehicle_id, scheduled_time):
        raise ValueError("Vehicle has an overlapping booking at the scheduled time.")
