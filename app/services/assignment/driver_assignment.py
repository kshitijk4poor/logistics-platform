from typing import Optional

from app.models import Driver
from app.services.caching.cache import cache_driver_availability
from app.services.tracking.driver_tracking import assign_driver_to_booking
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


async def get_driver_from_db(driver_id: int, db: AsyncSession) -> Optional[Driver]:
    """
    Fetch the complete Driver object from the database.
    """
    result = await db.execute(select(Driver).filter(Driver.id == driver_id))
    return result.scalar_one_or_none()


async def assign_driver(driver_id: int, booking_id: int, db: AsyncSession) -> bool:
    """
    Assign a driver to a booking by updating their availability and booking status.
    """
    driver = await get_driver_from_db(driver_id, db)
    if not driver:
        return False

    driver.is_available = False
    await db.commit()
    await db.refresh(driver)

    # Cache the driver's availability
    await cache_driver_availability(driver.id, False)

    # Assign driver to booking in Redis for tracking
    await assign_driver_to_booking(driver.id, booking_id)

    return True
