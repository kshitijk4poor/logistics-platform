import json
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.shape import to_shape

from app.models import Booking
from app.routes.tracking import manager

async def notify_nearby_drivers(booking_id: int, db: AsyncSession):
    booking = await db.get(Booking, booking_id)
    if not booking:
        return

    # Extract latitude and longitude from the Geometry object
    point = to_shape(booking.pickup_location)
    pickup_lat, pickup_lng = point.y, point.x

    vehicle_type = booking.vehicle_type

    # Find nearby drivers using H3
    nearby_driver_ids = manager.get_nearby_drivers(
        lat=pickup_lat, lng=pickup_lng, radius_km=5, vehicle_type=vehicle_type
    )

    # Notify each driver via WebSocket
    for driver_id in nearby_driver_ids:
        await manager.send_booking_assignment(driver_id, booking)


async def notify_driver_assignment(driver_id: int, booking_id: int):
    """
    Notify the driver about the new booking assignment via WebSocket.
    """
    message = json.dumps({
        "type": "assignment",
        "data": {
            "booking_id": booking_id,
            "message": "You have been assigned a new booking.",
            },
        }
    )

    await manager.send_message_to_driver(str(driver_id), message)
