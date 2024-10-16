import json

from fastapi import HTTPException

from app.services.communication.websocket_service import manager


async def notify_driver_assignment(driver_id: int, booking_id: int):
    """
    Notify the driver about the new booking assignment via WebSocket.
    """
    message = json.dumps(
        {
            "type": "assignment",
            "data": {
                "booking_id": booking_id,
                "message": "You have been assigned a new booking.",
            },
        }
    )
    await manager.send_message_to_driver(str(driver_id), message)


async def notify_nearby_drivers(booking_id: int, nearby_driver_ids: List[int]):
    """
    Notify all nearby drivers about a new booking.
    """
    message = json.dumps(
        {
            "type": "new_booking",
            "data": {
                "booking_id": booking_id,
                "message": "A new booking has been created near your location.",
            },
        }
    )
    for driver_id in nearby_driver_ids:
        await manager.send_message_to_driver(str(driver_id), message)
