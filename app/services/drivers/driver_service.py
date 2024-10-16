from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models import Driver
from app.schemas.driver import DriverCreate, DriverResponse

async def create_driver_service(driver_data: DriverCreate, db: AsyncSession) -> DriverResponse:
    new_driver = Driver(
        name=driver_data.name,
        email=driver_data.email,
        vehicle_type=driver_data.vehicle_type,
        is_available=True
    )
    db.add(new_driver)
    await db.commit()
    await db.refresh(new_driver)
    return new_driver

async def get_driver_service(driver_id: int, db: AsyncSession) -> DriverResponse:
    driver = await db.get(Driver, driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return driver