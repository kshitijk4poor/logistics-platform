from typing import Optional

import h3
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BookingRequest, Driver
from app.services.pricing import get_h3_index


async def assign_driver(
    booking_data: BookingRequest, db: AsyncSession
) -> Optional[Driver]:
    """
    Assign the nearest available driver based on pickup location and vehicle type.
    """
    # Extract pickup coordinates
    pickup_lat = booking_data.pickup_latitude
    pickup_lng = booking_data.pickup_longitude
    vehicle_type = booking_data.vehicle_type

    # Get H3 index for the pickup location
    pickup_h3 = get_h3_index(pickup_lat, pickup_lng)

    # Query available drivers matching the vehicle type
    result = await db.execute(
        select(Driver).where(
            Driver.is_available == True,
            Driver.vehicle_type == vehicle_type,
        )
    )
    available_drivers = result.scalars().all()

    if not available_drivers:
        return None

    # Find the nearest driver using H3
    nearest_driver = None
    min_hex_distance = float("inf")

    for driver in available_drivers:
        if driver.location:
            driver_h3 = get_h3_index(
                driver.location.y, driver.location.x
            )  # Assuming POINT(lon lat)
            hex_distance = h3.h3_distance(pickup_h3, driver_h3)
            if hex_distance < min_hex_distance:
                min_hex_distance = hex_distance
                nearest_driver = driver

    if nearest_driver:
        # Assign driver by marking as unavailable
        nearest_driver.is_available = False
        await db.commit()
        await db.refresh(nearest_driver)
        return nearest_driver

    return None
