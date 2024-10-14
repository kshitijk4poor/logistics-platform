import json
import time
import h3
from typing import List, Dict, Any

import aioredis
from fastapi import HTTPException

REDIS_URL = "redis://localhost"


async def get_redis():
    return await aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)


async def update_driver_location(driver_id: int, latitude: float, longitude: float, vehicle_type: str):
    """
    Update the driver's location in Redis and maintain H3 index sets.
    """
    redis = await get_redis()
    
    # Update driver's location
    location_key = f"driver:location:{driver_id}"
    location_data = json.dumps({
        "lat": latitude,
        "lng": longitude,
        "timestamp": int(time.time())
    })
    await redis.set(location_key, location_data)
    
    # Update H3 index sets
    h3_index = h3.geo_to_h3(latitude, longitude, 9)  # Adjust resolution as needed
    
    # Remove driver from old H3 index set (if exists)
    old_h3_index = await redis.get(f"driver:h3:{driver_id}")
    if old_h3_index:
        await redis.srem(f"drivers:{old_h3_index}:{vehicle_type}", driver_id)
    
    # Add driver to new H3 index set
    await redis.sadd(f"drivers:{h3_index}:{vehicle_type}", driver_id)
    await redis.set(f"driver:h3:{driver_id}", h3_index)
    
    # Set expiration for all keys
    await redis.expire(location_key, 300)  # 5 minutes
    await redis.expire(f"drivers:{h3_index}:{vehicle_type}", 300)
    await redis.expire(f"driver:h3:{driver_id}", 300)


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


async def update_driver_locations(driver_updates: List[Dict[str, Any]]):
    """
    Update multiple drivers' locations in Redis and maintain H3 index sets.
    """
    redis = await get_redis()
    pipeline = redis.pipeline()
    
    for update in driver_updates:
        driver_id = update['driver_id']
        latitude = update['latitude']
        longitude = update['longitude']
        vehicle_type = update['vehicle_type']
        
        # Update driver's location
        location_key = f"driver:location:{driver_id}"
        location_data = json.dumps({
            "lat": latitude,
            "lng": longitude,
            "timestamp": int(time.time())
        })
        pipeline.set(location_key, location_data)
        
        # Update H3 index sets
        h3_index = h3.geo_to_h3(latitude, longitude, 9)  # Adjust resolution as needed
        
        # Remove driver from old H3 index set (if exists)
        old_h3_index = await redis.get(f"driver:h3:{driver_id}")
        if old_h3_index:
            pipeline.srem(f"drivers:{old_h3_index}:{vehicle_type}", driver_id)
        
        # Add driver to new H3 index set
        pipeline.sadd(f"drivers:{h3_index}:{vehicle_type}", driver_id)
        pipeline.set(f"driver:h3:{driver_id}", h3_index)
        
        # Set expiration for all keys
        pipeline.expire(location_key, 300)  # 5 minutes
        pipeline.expire(f"drivers:{h3_index}:{vehicle_type}", 300)
        pipeline.expire(f"driver:h3:{driver_id}", 300)
    
    # Execute all Redis commands in a single batch
    await pipeline.execute()