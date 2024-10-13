from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import cache, rate_limit
from app.models import Booking
from app.schemas.booking import BookingRequest, BookingResponse
from app.services.matching import assign_driver
from app.services.pricing import calculate_price
from db.database import get_db

router = APIRouter()


@router.post("/book", response_model=BookingResponse)
@rate_limit(max_calls=5, time_frame=60)
async def create_booking(
    booking_data: BookingRequest,
    background_tasks: BackgroundTasks,
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

        price = await calculate_price(booking_data.dict())

        driver = await assign_driver(booking_data, db)

        if not driver:
            raise HTTPException(status_code=404, detail="No available drivers found")

        # Create booking
        booking = Booking(
            user_id=booking_data.user_id,
            driver_id=driver.id,
            pickup_location=f"POINT({booking_data.pickup_longitude} {booking_data.pickup_latitude})",
            dropoff_location=f"POINT({booking_data.dropoff_longitude} {booking_data.dropoff_latitude})",
            vehicle_type=booking_data.vehicle_type,
            price=price,
            date=booking_data.scheduled_time or datetime.now(),
            status="pending",
        )

        db.add(booking)
        await db.commit()
        await db.refresh(booking)

        await cache.set(
            cache_key, {"id": booking.id, "price": price}, expire=300
        )  # Cache for 5 minutes

        background_tasks.add_task(notify_driver, driver.id, booking.id)
        background_tasks.add_task(update_analytics, booking.id, db)

        return JSONResponse(
            content={"booking_id": booking.id, "price": price, "status": "confirmed"}
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/booking/{booking_id}")
async def get_booking(booking_id: int, db: AsyncSession = Depends(get_db)):
    booking = await db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.put("/booking/{booking_id}/cancel")
async def cancel_booking(booking_id: int, db: AsyncSession = Depends(get_db)):
    booking = await db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot cancel a completed booking")

    booking.status = "cancelled"
    await db.commit()
    return {"status": "cancelled"}


async def notify_driver(driver_id: int, booking_id: int):
    # Implement driver notification logic (e.g., push notification)
    pass


async def update_analytics(booking_id: int, db: AsyncSession):
    # Implementation
    pass
