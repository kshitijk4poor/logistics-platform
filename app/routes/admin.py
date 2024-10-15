from typing import List

from app.dependencies import get_current_admin
from app.models import Vehicle
from app.schemas.vehicles import VehicleResponse, VehicleSchema, VehicleUpdate
from db.database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter()


@router.get(
    "/admin/fleet",
    dependencies=[Depends(get_current_admin)],
    response_model=List[VehicleResponse],
)
async def get_fleet(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vehicle))
    vehicles = result.scalars().all()
    return vehicles


@router.post(
    "/admin/fleet",
    dependencies=[Depends(get_current_admin)],
    status_code=status.HTTP_201_CREATED,
)
async def add_vehicle(vehicle_data: VehicleSchema, db: AsyncSession = Depends(get_db)):
    vehicle = Vehicle(**vehicle_data.dict())
    db.add(vehicle)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle


@router.put(
    "/admin/fleet/{vehicle_id}",
    dependencies=[Depends(get_current_admin)],
    response_model=VehicleResponse,
)
async def update_vehicle(
    vehicle_id: int, vehicle_data: VehicleUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Vehicle).filter(Vehicle.id == vehicle_id))
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    for key, value in vehicle_data.dict(exclude_unset=True).items():
        setattr(vehicle, key, value)

    await db.commit()
    await db.refresh(vehicle)
    return vehicle


@router.delete(
    "/admin/fleet/{vehicle_id}",
    dependencies=[Depends(get_current_admin)],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_vehicle(vehicle_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vehicle).filter(Vehicle.id == vehicle_id))
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    await db.delete(vehicle)
    await db.commit()
    return None
