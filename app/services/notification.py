from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import Booking, BookingStatusEnum, Driver
from app.routes.tracking import manager


async def notify_nearby_drivers(booking_id: int, db: AsyncSession):
    # Fetch the booking details
    booking = await db.get(Booking, booking_id)
    if not booking:
        return

    pickup_lat, pickup_lng = parse_point(booking.pickup_location)
    vehicle_type = booking.vehicle_type

    # Find nearby drivers using H3
    nearby_driver_ids = manager.get_nearby_drivers(
        lat=pickup_lat, lng=pickup_lng, radius_km=5, vehicle_type=vehicle_type
    )

    # Notify each driver via WebSocket
    for driver_id in nearby_driver_ids:
        await manager.send_booking_assignment(driver_id, booking)


def parse_point(point_str: str):
    try:
        _, coords = point_str.split("(")
        coords = coords.strip(")")
        lng, lat = map(float, coords.split())
        return lat, lng
    except Exception:
        return 0.0, 0.0
