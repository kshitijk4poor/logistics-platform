import h3
from geoalchemy2.functions import ST_Distance
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.models import Driver
from app.routes.tracking import manager
from app.schemas.bookings import BookingRequest

async def assign_driver(booking_data: BookingRequest, db: AsyncSession) -> Optional[Driver]:
    stmt = (
        select(Driver)
        .where(
            Driver.is_available == True,
            func.ST_DWithin(
                Driver.location,
                func.ST_SetSRID(
                    func.ST_MakePoint(
                        booking_data.pickup_longitude, booking_data.pickup_latitude
                    ),
                    4326,
                ),
                10000  # 10 km in meters
            ),
            Driver.vehicle_type == booking_data.vehicle_type,
        )
        .order_by(
            func.ST_Distance(
                Driver.location,
                func.ST_SetSRID(
                    func.ST_MakePoint(
                        booking_data.pickup_longitude, booking_data.pickup_latitude
                    ),
                    4326,
                ),
            )
        )
        .limit(1)
    )
    driver = await db.execute(stmt)
    return driver.scalar_one_or_none()