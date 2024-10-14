from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.dependencies import get_current_driver, get_db
from app.models import Booking, BookingStatusEnum, Driver
from app.schemas.booking import BookingStatus, StatusUpdateRequest
from app.schemas.driver import AcceptBookingResponse, LocationUpdate
from app.services.notification import notify_user
from app.services.tracking import (
    assign_driver_to_booking,
    clear_driver_assignment,
    update_driver_location,
)
from app.tasks import handle_booking_completion, update_analytics

router = APIRouter(prefix="/driver", tags=["drivers"])


@router.post("/accept_booking/{booking_id}", response_model=AcceptBookingResponse)
async def accept_booking(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_driver: Driver = Depends(get_current_driver),
):
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()

    if (
        not booking
        or booking.driver_id != current_driver.id
        or booking.status != BookingStatusEnum.pending
    ):
        raise HTTPException(status_code=400, detail="Invalid booking or status")

    booking.status = BookingStatusEnum.confirmed
    booking.status_history.append(
        {"status": BookingStatusEnum.confirmed, "timestamp": datetime.utcnow()}
    )
    await db.commit()
    await db.refresh(booking)

    await notify_user(
        booking.user_id, f"Your booking {booking_id} has been accepted by a driver."
    )
    await assign_driver_to_booking(current_driver.id, booking_id)

    return AcceptBookingResponse(
        booking_id=booking.id,
        pickup_location=booking.pickup_location,
        dropoff_location=booking.dropoff_location,
        vehicle_type=booking.vehicle_type,
        price=booking.price,
        scheduled_time=booking.date,
        status=booking.status,
    )


@router.post("/update_status/{booking_id}", status_code=status.HTTP_200_OK)
async def update_job_status(
    booking_id: int,
    status_update: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_driver: Driver = Depends(get_current_driver),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()

    if not booking or booking.driver_id != current_driver.id:
        raise HTTPException(status_code=400, detail="Invalid booking")

    if not is_valid_status_transition(booking.status, status_update.status):
        raise HTTPException(status_code=400, detail="Invalid status transition")

    booking.status = status_update.status
    booking.status_history.append(
        {"status": status_update.status, "timestamp": datetime.utcnow()}
    )
    await db.commit()
    await db.refresh(booking)

    await notify_user(
        booking.user_id,
        f"Your booking {booking_id} status has been updated to {status_update.status}",
    )

    if status_update.status in [
        BookingStatusEnum.completed,
        BookingStatusEnum.cancelled,
    ]:
        current_driver.is_available = True
        await db.commit()
        await clear_driver_assignment(current_driver.id, booking_id)
        background_tasks.add_task(handle_booking_completion, booking_id)
        background_tasks.add_task(update_analytics, booking_id)

    return {"detail": f"Booking status updated to {status_update.status}"}


@router.post("/update_location", status_code=status.HTTP_200_OK)
async def update_location(
    location: LocationUpdate,
    current_driver: Driver = Depends(get_current_driver),
):
    await update_driver_location(
        current_driver.id, location.latitude, location.longitude
    )
    return {"detail": "Location updated successfully"}


def is_valid_status_transition(
    current_status: BookingStatusEnum, new_status: BookingStatusEnum
) -> bool:
    valid_transitions = {
        BookingStatusEnum.confirmed: [
            BookingStatusEnum.en_route,
            BookingStatusEnum.cancelled,
        ],
        BookingStatusEnum.en_route: [
            BookingStatusEnum.goods_collected,
            BookingStatusEnum.cancelled,
        ],
        BookingStatusEnum.goods_collected: [
            BookingStatusEnum.delivered,
            BookingStatusEnum.cancelled,
        ],
        BookingStatusEnum.delivered: [BookingStatusEnum.completed],
    }
    return new_status in valid_transitions.get(current_status, [])