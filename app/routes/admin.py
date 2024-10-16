from typing import List

from app.dependencies import get_current_admin, get_db
from app.schemas.vehicles import VehicleResponse, VehicleSchema, VehicleUpdate
from app.services.admin.admin_service import (
    add_vehicle,
    delete_vehicle,
    get_fleet,
    update_vehicle,
)
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get(
    "/admin/fleet",
    dependencies=[Depends(get_current_admin)],
    response_model=List[VehicleResponse],
)
async def get_fleet_route(db: AsyncSession = Depends(get_db)):
    vehicles = await get_fleet(db)
    return vehicles


@router.post(
    "/admin/fleet",
    dependencies=[Depends(get_current_admin)],
    status_code=status.HTTP_201_CREATED,
    response_model=VehicleResponse,
)
async def add_vehicle_route(
    vehicle_data: VehicleSchema, db: AsyncSession = Depends(get_db)
):
    vehicle = await add_vehicle(vehicle_data, db)
    return vehicle


@router.put(
    "/admin/fleet/{vehicle_id}",
    dependencies=[Depends(get_current_admin)],
    response_model=VehicleResponse,
)
async def update_vehicle_route(
    vehicle_id: int, vehicle_data: VehicleUpdate, db: AsyncSession = Depends(get_db)
):
    vehicle = await update_vehicle(vehicle_id, vehicle_data, db)
    return vehicle


@router.delete(
    "/admin/fleet/{vehicle_id}",
    dependencies=[Depends(get_current_admin)],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_vehicle_route(vehicle_id: int, db: AsyncSession = Depends(get_db)):
    await delete_vehicle(vehicle_id, db)
