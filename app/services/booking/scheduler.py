import asyncio
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, BookingStatusEnum
from app.services.assignment.matching import find_nearest_driver
from app.services.communication.notification import notify_driver_assignment
from app.services.messaging.kafka_service import (KAFKA_TOPIC_BOOKING_UPDATES,
                                                  kafka_service)
from app.services.validation.validation import validate_booking
from db.database import get_db


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
        booking.status_history.append(
            {"status": BookingStatusEnum.confirmed, "timestamp": datetime.utcnow()}
        )
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
