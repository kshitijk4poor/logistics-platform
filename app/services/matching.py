from typing import Optional

import h3
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Driver
from app.routes.tracking import (
    manager,
)  # Ensure this import path is correct based on your project structure
from app.schemas.booking import BookingRequest


async def assign_driver(
    booking_data: BookingRequest, db: AsyncSession
) -> Optional[Driver]:
    """
    Assign the nearest available driver based on the pickup location and vehicle type using H3 indexing.

    Args:
        booking_data (BookingRequest): The booking request containing pickup/dropoff details and vehicle type.
        db (AsyncSession): The database session.

    Returns:
        Optional[Driver]: The assigned driver if available, else None.
    """
    pickup_lat = booking_data.pickup_latitude
    pickup_lng = booking_data.pickup_longitude
    vehicle_type = booking_data.vehicle_type

    # Define H3 resolution (9 ~ 150m)
    h3_resolution = 9
    pickup_h3 = h3.geo_to_h3(pickup_lat, pickup_lng, h3_resolution)

    # Maximum number of rings to search (e.g., 10 km radius)
    max_k = 24  # Adjust based on desired search radius and H3 resolution

    for k in range(max_k + 1):
        # Get H3 indices in the current ring
        search_h3_indices = h3.k_ring(pickup_h3, k)

        candidate_driver_ids = [
            driver_id
            for driver_id, info in manager.driver_locations.items()
            if info["h3_index"] in search_h3_indices
            and info["vehicle_type"] == vehicle_type
            and info["is_available"]
        ]

        if not candidate_driver_ids:
            continue  # Expand search radius

        # Query drivers from the database
        stmt = (
            select(Driver)
            .where(
                Driver.id.in_(candidate_driver_ids),
                Driver.is_available == True,
                Driver.vehicle_type == vehicle_type,
            )
            .order_by(
                func.ST_Distance(
                    Driver.location,
                    func.ST_SetSRID(func.ST_MakePoint(pickup_lng, pickup_lat), 4326),
                )
            )
            .limit(1)
        )

        result = await db.execute(stmt)
        driver = result.scalar_one_or_none()

        if driver:
            # Update driver's availability to prevent double assignment
            driver.is_available = False
            await db.commit()
            return driver

    # No available driver found within the maximum search radius
    return None
