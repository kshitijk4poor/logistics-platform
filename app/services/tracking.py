import json
import time

import aioredis
from fastapi import HTTPException

REDIS_URL = "redis://localhost"


async def get_redis():
    return await aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)


async def update_driver_location(driver_id: int, latitude: float, longitude: float):
    """
    Update the driver's location in Redis.
    """
    redis = await get_redis()
    location_key = f"driver:location:{driver_id}"
    location_data = json.dumps(
        {"latitude": latitude, "longitude": longitude, "timestamp": int(time.time())}
    )
    await redis.set(location_key, location_data)
    await redis.expire(location_key, 300)  # Expire after 5 minutes


async def get_driver_location(driver_id: int):
    """
    Retrieve the driver's last known location from Redis.
    """
    redis = await get_redis()
    location_key = f"driver:location:{driver_id}"
    location_data = await redis.get(location_key)

    if not location_data:
        raise HTTPException(status_code=404, detail="Driver location not found")

    return json.loads(location_data)


async def assign_driver_to_booking(driver_id: int, booking_id: int):
    """
    Assign a driver to a booking in Redis for tracking purposes.
    """
    redis = await get_redis()
    await redis.set(f"booking:driver:{booking_id}", str(driver_id))
    await redis.set(f"driver:current_booking:{driver_id}", str(booking_id))


async def get_driver_for_booking(booking_id: int):
    """
    Get the driver assigned to a specific booking.
    """
    redis = await get_redis()
    driver_id = await redis.get(f"booking:driver:{booking_id}")
    if not driver_id:
        raise HTTPException(
            status_code=404, detail="No driver assigned to this booking"
        )
    return int(driver_id)


async def clear_driver_assignment(driver_id: int, booking_id: int):
    """
    Clear the driver assignment after a booking is completed or cancelled.
    """
    redis = await get_redis()
    await redis.delete(f"booking:driver:{booking_id}")
    await redis.delete(f"driver:current_booking:{driver_id}")


async def get_active_bookings_for_driver(driver_id: int):
    """
    Get all active bookings for a driver.
    """
    redis = await get_redis()
    booking_id = await redis.get(f"driver:current_booking:{driver_id}")
    if booking_id:
        return [int(booking_id)]
    return []


async def update_booking_status(booking_id: int, status: str):
    """
    Update the booking status in Redis for real-time tracking.
    """
    redis = await get_redis()
    await redis.set(f"booking:status:{booking_id}", status)
    await redis.expire(f"booking:status:{booking_id}", 86400)  # Expire after 24 hours


async def get_booking_status(booking_id: int):
    """
    Get the current status of a booking from Redis.
    """
    redis = await get_redis()
    status = await redis.get(f"booking:status:{booking_id}")
    if not status:
        raise HTTPException(status_code=404, detail="Booking status not found")
    return status


async def get_redis_connection():
    return await aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)


async def publish_location(driver_id: str, latitude: float, longitude: float):
    redis = await get_redis_connection()
    location_data = json.dumps(
        {
            "driver_id": driver_id,
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": int(time.time()),
        }
    )
    await redis.publish("driver_locations", location_data)
    await redis.close()
