from typing import List

from app.models import Vehicle
from app.schemas.vehicles import VehicleResponse, VehicleSchema, VehicleUpdate
from app.services.caching.cache import cache
from app.services.db_utils import get_vehicle_by_id
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


async def get_fleet(db: AsyncSession) -> List[VehicleResponse]:
    result = await db.execute(select(Vehicle))
    vehicles = result.scalars().all()
    return vehicles


async def add_vehicle(vehicle_data: VehicleSchema, db: AsyncSession) -> Vehicle:
    vehicle = Vehicle(**vehicle_data.dict())
    db.add(vehicle)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle


async def update_vehicle(
    vehicle_id: int, vehicle_data: VehicleUpdate, db: AsyncSession
) -> Vehicle:
    vehicle = await get_vehicle_by_id(db, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    for key, value in vehicle_data.dict(exclude_unset=True).items():
        setattr(vehicle, key, value)

    await db.commit()
    await db.refresh(vehicle)
    return vehicle


async def delete_vehicle(vehicle_id: int, db: AsyncSession) -> None:
    result = await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    await db.delete(vehicle)
    await db.commit()
