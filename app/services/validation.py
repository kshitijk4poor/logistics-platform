from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import Booking, MaintenancePeriod, BookingStatusEnum

async def is_overlapping_booking(
    db: AsyncSession, vehicle_id: int, scheduled_time: datetime, duration_minutes: int = 60
) -> bool:
    """
    Check if the vehicle has any bookings overlapping with the scheduled_time.
    Assumes each booking has a fixed duration; adjust as needed.
    """
    end_time = scheduled_time + timedelta(minutes=duration_minutes)
    overlap_query = select(Booking).where(
        Booking.driver_id == vehicle_id,
        Booking.status.notin_([BookingStatusEnum.cancelled, BookingStatusEnum.completed]),
        Booking.date < end_time,
        (Booking.date + timedelta(minutes=duration_minutes)) > scheduled_time
    )
    result = await db.execute(overlap_query)
    overlapping_booking = result.scalar_one_or_none()
    return overlapping_booking is not None

async def is_under_maintenance(
    db: AsyncSession, vehicle_id: int, scheduled_time: datetime
) -> bool:
    """
    Check if the vehicle is under maintenance during the scheduled_time.
    """
    maintenance_query = select(MaintenancePeriod).where(
        MaintenancePeriod.vehicle_id == vehicle_id,
        MaintenancePeriod.start_time <= scheduled_time,
        MaintenancePeriod.end_time >= scheduled_time
    )
    result = await db.execute(maintenance_query)
    maintenance = result.scalar_one_or_none()
    return maintenance is not None

async def validate_booking(
    db: AsyncSession, vehicle_id: int, scheduled_time: datetime
):
    """
    Validate that the vehicle is available for the scheduled_time.
    """
    if await is_overlapping_booking(db, vehicle_id, scheduled_time):
        raise ValueError("Vehicle is already booked for the selected time.")

    if await is_under_maintenance(db, vehicle_id, scheduled_time):
        raise ValueError("Vehicle is under maintenance during the selected time.")