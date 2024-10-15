from datetime import datetime

from app.models import Booking, BookingStatusEnum
from app.services.assignment import assign_driver
from app.services.notification import notify_driver_assignment
from app.services.validation import validate_booking
from db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession


async def process_immediate_booking(booking_id: int):
    async with get_db() as db:
        booking = await db.get(Booking, booking_id)
        if not booking:
            # Handle missing booking
            return

        if booking.status != BookingStatusEnum.pending:
            # Booking is not in pending status, possibly already processed
            return

        # Assign driver
        assigned_driver = await assign_driver(booking, db)
        if not assigned_driver:
            # Handle no available driver
            booking.status = BookingStatusEnum.cancelled
            await db.commit()
            return

        # Validate booking time
        await validate_booking(db, assigned_driver.vehicle.id, booking.date)

        # Update booking with driver assignment
        booking.driver_id = assigned_driver.id
        booking.status = BookingStatusEnum.confirmed
        booking.status_history.append(
            {"status": BookingStatusEnum.confirmed, "timestamp": datetime.utcnow()}
        )
        await db.commit()

        # Notify driver about the assignment
        await notify_driver_assignment(assigned_driver.id, booking.id)
