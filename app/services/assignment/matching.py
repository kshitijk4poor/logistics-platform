from typing import Optional

import h3
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BookingRequest, Driver
from app.services.assignment.driver_assignment import assign_driver
from app.services.caching.cache import get_redis_client
from app.services.tracking.driver_tracking import get_driver_location

from .driver_assignment import get_driver_from_db


async def find_nearest_driver(
    booking_data: BookingRequest, db: AsyncSession
) -> Optional[Driver]:
    """
    Assign the nearest available driver based on pickup location and vehicle type.
    """
    pickup_lat = booking_data.pickup_latitude
    pickup_lng = booking_data.pickup_longitude
    vehicle_type = booking_data.vehicle_type

    pickup_h3 = h3.geo_to_h3(pickup_lat, pickup_lng, 9)

    redis = await get_redis_client()

    # Search for drivers in expanding hexagon rings
    for k in range(5):  # Adjust the range based on coverage needs
        hex_ring = h3.k_ring(pickup_h3, k)
        for hex_index in hex_ring:
            drivers = await redis.smembers(f"drivers:{hex_index}:{vehicle_type}")
            if drivers:
                nearest_driver = await select_nearest_driver(drivers, pickup_h3, redis)
                if nearest_driver:
                    # Assign driver to booking
                    success = await assign_driver(nearest_driver, booking_data.id, db)
                    if success:
                        return await get_driver_from_db(nearest_driver, db)

    return None


async def select_nearest_driver(drivers: set, pickup_h3: str, redis) -> Optional[int]:
    """
    Select the nearest driver from a set of drivers based on H3 distance.
    """
    min_distance = float("inf")
    nearest_driver = None

    for driver_id in drivers:
        location = await get_driver_location(int(driver_id))
        if location:
            driver_h3 = h3.geo_to_h3(location["lat"], location["lng"], 9)
            distance = h3.h3_distance(pickup_h3, driver_h3)
            if distance < min_distance:
                min_distance = distance
                nearest_driver = int(driver_id)

    return nearest_driver
