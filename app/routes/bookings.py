import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.dependencies import cache, get_current_user, rate_limit
from app.models import Booking, BookingStatusEnum, Driver, RoleEnum, User
from app.schemas.booking import BookingRequest, BookingResponse
from app.services.immediate_booking import process_immediate_booking
from app.services.matching import assign_driver
from app.services.notification import notify_driver_assignment, notify_nearby_drivers
from app.services.pricing import calculate_price
from app.services.validation import validate_booking
from app.tasks import compute_analytics, schedule_booking_processing
from db.database import get_db

router = APIRouter()


@router.post("/book", response_model=BookingResponse)
@rate_limit(max_calls=5, time_frame=60)
async def create_booking(
    booking_data: BookingRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        # Check cache for recent identical booking
        cache_key = f"booking:{booking_data.user_id}:{booking_data.pickup_latitude},{booking_data.pickup_longitude}:{booking_data.dropoff_latitude},{booking_data.dropoff_longitude}"
        cached_booking = await cache.get(cache_key)
        if cached_booking:
            return JSONResponse(
                content={
                    "booking_id": cached_booking["id"],
                    "price": cached_booking["price"],
                    "status": "cached",
                }
            )

        # Calculate price
        price = await calculate_price(booking_data.dict())

        # Determine if booking is scheduled
        scheduled_time = booking_data.scheduled_time or datetime.utcnow()
        is_scheduled = (
            booking_data.scheduled_time is not None
            and booking_data.scheduled_time > datetime.utcnow()
        )

        # Set booking status based on scheduling
        status = (
            BookingStatusEnum.scheduled if is_scheduled else BookingStatusEnum.pending
        )

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
            await db.flush()  # This will populate the booking.id

            # Cache the booking
            await cache.set(cache_key, {"id": booking.id, "price": price}, expire=300)

            if is_scheduled:
                # Schedule background task to process booking at scheduled_time
                background_tasks.add_task(
                    schedule_booking_processing, booking.id, scheduled_time
                )
                booking_status = "scheduled"
            else:
                # Process immediate booking
                background_tasks.add_task(process_immediate_booking, booking.id)
                booking_status = "pending"

        return JSONResponse(
            content={
                "booking_id": booking.id,
                "price": price,
                "status": booking_status,
            }
        )

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/booking/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    booking = await db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.user_id != current_user.id and current_user.role.name != RoleEnum.admin:
        raise HTTPException(
            status_code=403, detail="Not authorized to view this booking"
        )
    return booking


@router.put("/booking/{booking_id}/cancel")
async def cancel_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    booking = await db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.user_id != current_user.id and current_user.role.name != RoleEnum.admin:
        raise HTTPException(
            status_code=403, detail="Not authorized to cancel this booking"
        )
    if booking.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot cancel a completed booking")

    booking.status = "cancelled"
    await db.commit()
    return {"status": "cancelled"}


async def notify_driver(driver_id: int, booking_id: int):
    """
    Notify the driver about the new booking.
    This could be implemented via WebSocket, push notifications, email, etc.
    """
    # Example implementation using WebSocket manager
    # You might need to implement a WebSocket connection for drivers to receive notifications
    pass


async def update_analytics(booking_id: int, db: AsyncSession):
    """
    Update analytics data after a new booking is created.
    This increments necessary counters and triggers a Celery task to recompute full analytics.
    """
    try:
        # Fetch the new booking
        booking = await db.get(Booking, booking_id)
        if not booking:
            logging.error(f"Booking not found for ID: {booking_id}")
            return

        # Increment counters in Redis
        redis = await cache.get_client()
        pipe = redis.pipeline()

        # Increment total bookings
        pipe.incr("analytics:total_bookings")

        # Increment total revenue
        pipe.incrbyfloat("analytics:total_revenue", booking.price)

        # Update average price
        pipe.rpush("analytics:recent_prices", booking.price)
        pipe.ltrim("analytics:recent_prices", -100, -1)  # Keep only last 100 prices

        # Increment pickup location count
        pickup_key = f"analytics:pickup:{booking.pickup_location}"
        pipe.incr(pickup_key)

        # Execute Redis pipeline
        await pipe.execute()

        # Update active drivers count (this might change frequently, so we recompute)
        active_drivers = await db.scalar(
            select(func.count(Driver.id)).where(Driver.is_available == True)
        )
        await redis.set("analytics:active_drivers", active_drivers)

        # Trigger full analytics recomputation
        from app.tasks import compute_analytics

        compute_analytics.delay()

        logging.info(f"Analytics incrementally updated for booking ID: {booking_id}")
    except Exception as e:
        logging.error(f"Error updating analytics for booking ID {booking_id}: {e}")
