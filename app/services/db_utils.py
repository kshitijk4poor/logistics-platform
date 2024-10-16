from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import Driver, Vehicle


async def get_vehicle_by_id(db: AsyncSession, vehicle_id: int) -> Vehicle:
    result = await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
    return result.scalar_one_or_none()


async def get_driver_by_id(db: AsyncSession, driver_id: int) -> Driver:
    result = await db.execute(select(Driver).where(Driver.id == driver_id))
    return result.scalar_one_or_none()
