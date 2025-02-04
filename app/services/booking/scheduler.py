import asyncio
from datetime import datetime

from app.models import Booking, BookingStatusEnum, BookingStatusHistory
from app.services.assignment.matching import find_nearest_driver
from app.services.communication.notification import notify_driver_assignment
from app.services.messaging.kafka_service import (KAFKA_TOPIC_BOOKING_UPDATES,
                                                  kafka_service)
from app.services.validation.validation import validate_booking
from db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession


async def process_scheduled_booking(booking_id: int):
    async with get_db() as db:
        booking = await db.get(Booking, booking_id)
        if not booking:
            # Handle missing booking
            return

        if booking.status != BookingStatusEnum.scheduled:
            # Booking is not in scheduled status, possibly already processed
            return

        # Assign driver
        assigned_driver = await find_nearest_driver(booking, db)
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

        # Add status change to BookingStatusHistory
        status_history_entry = BookingStatusHistory(
            booking_id=booking.id,
            status=BookingStatusEnum.confirmed,
            timestamp=datetime.utcnow(),
        )
        db.add(status_history_entry)

        await db.commit()

        # Notify driver about the assignment
        await notify_driver_assignment(assigned_driver.id, booking.id)

        # Publish booking update to Kafka
        await kafka_service.send_message(
            KAFKA_TOPIC_BOOKING_UPDATES,
            {
                "booking_id": booking.id,
                "status": BookingStatusEnum.confirmed,
                "driver_id": assigned_driver.id,
            },
        )
