from typing import Optional

import h3
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BookingRequest, Driver
from app.services.pricing import get_h3_index
from app.services.tracking import (
    assign_driver_to_booking,
    get_redis,
)


async def assign_driver(
    booking_data: BookingRequest, db: AsyncSession
) -> Optional[Driver]:
    """
    Assign the nearest available driver based on pickup location and vehicle type.
    """
    pickup_lat = booking_data.pickup_latitude
    pickup_lng = booking_data.pickup_longitude
    vehicle_type = booking_data.vehicle_type

    pickup_h3 = get_h3_index(pickup_lat, pickup_lng)

    redis = await get_redis()

    # Search for drivers in expanding hexagon rings
    for k in range(5):  # Adjust the range based on your coverage needs
        hex_ring = h3.k_ring(pickup_h3, k)
        for hex_index in hex_ring:
            drivers = await redis.smembers(f"drivers:{hex_index}:{vehicle_type}")
            if drivers:
                nearest_driver = await find_nearest_driver(drivers, pickup_h3, redis)
                if nearest_driver:
                    await assign_driver_to_booking(nearest_driver, booking_data.id)
                    return await get_driver_from_db(nearest_driver, db)

    return None


async def find_nearest_driver(drivers, pickup_h3, redis):
    min_distance = float("inf")
    nearest_driver = None
    for driver_id in drivers:
        driver_location = await redis.get(f"driver:location:{driver_id}")
        if driver_location:
            driver_h3 = h3.geo_to_h3(driver_location["lat"], driver_location["lng"], 9)
            distance = h3.h3_distance(pickup_h3, driver_h3)
            if distance < min_distance:
                min_distance = distance
                nearest_driver = driver_id
    return nearest_driver


async def get_driver_from_db(driver_id: str, db: AsyncSession) -> Optional[Driver]:
    """
    Fetch the complete Driver object from the database.
    """
    result = await db.execute(select(Driver).filter(Driver.id == driver_id))
    return result.scalar_one_or_none()
