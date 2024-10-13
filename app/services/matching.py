from typing import Optional

import h3
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Driver
from app.schemas.booking import BookingRequest


async def assign_driver(
    booking_data: BookingRequest, db: AsyncSession
) -> Optional[Driver]:
    pickup_point = func.ST_SetSRID(
        func.ST_MakePoint(booking_data.pickup_longitude, booking_data.pickup_latitude),
        4326,
    )

    stmt = (
        select(Driver)
        .where(
            Driver.is_available == True,
            func.ST_DWithin(Driver.location, pickup_point, 10000),  # 10 km in meters
            Driver.vehicle_type == booking_data.vehicle_type,
        )
        .order_by(func.ST_Distance(Driver.location, pickup_point))
        .limit(1)
    )

    result = await db.execute(stmt)
    driver = result.scalar_one_or_none()
    return driver
