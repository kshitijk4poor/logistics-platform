from datetime import datetime
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, BookingStatusEnum, User
from app.schemas.booking import BookingRequest, BookingResponse
from app.services.pricing import calculate_price
from app.services.validation import validate_booking
from app.services.caching.cache import cache
from app.tasks import process_immediate_booking, schedule_booking_processing

async def create_new_booking(
    booking_data: BookingRequest,
    current_user: User,
    db: AsyncSession,
    background_tasks: BackgroundTasks
) -> BookingResponse:
    """
    Create a new booking and handle subsequent operations.
    """
    try:
        # Calculate price
        price = await calculate_price(booking_data.dict())

        # Determine if booking is scheduled
        scheduled_time = booking_data.scheduled_time or datetime.utcnow()
        is_scheduled = (
            booking_data.scheduled_time is not None
            and booking_data.scheduled_time > datetime.utcnow()
        )

        # Set booking status based on scheduling
        status = BookingStatusEnum.scheduled if is_scheduled else BookingStatusEnum.pending

        # Validate booking
        await validate_booking(db, booking_data.vehicle_type, scheduled_time)

        async with db.begin():
            # Create booking
            booking = Booking(
                user_id=current_user.id,
                pickup_location=f"POINT({booking_data.pickup_longitude} {booking_data.pickup_latitude})",
                dropoff_location=f"POINT({booking_data.dropoff_longitude} {booking_data.dropoff_latitude})",
                vehicle_type=booking_data.vehicle_type,
                price=price,
                date=scheduled_time,
                status=status,
                status_history=[{"status": status, "timestamp": datetime.utcnow()}],
            )
            db.add(booking)
            await db.flush()  # Populate booking.id

            # Cache the booking
            cache_key = f"booking:{booking_data.user_id}:{booking_data.pickup_latitude},{booking_data.pickup_longitude}:{booking_data.dropoff_latitude},{booking_data.dropoff_longitude}"
            await cache.set(cache_key, {"id": booking.id, "price": price}, expire=300)

            if is_scheduled:
                # Schedule background task for scheduled booking
                background_tasks.add_task(schedule_booking_processing, booking.id, scheduled_time)
                booking_status = "scheduled"
            else:
                # Process immediate booking
                background_tasks.add_task(process_immediate_booking, booking.id)
                booking_status = "pending"

        return BookingResponse(
            booking_id=booking.id,
            price=price,
            status=booking_status,
        )

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))