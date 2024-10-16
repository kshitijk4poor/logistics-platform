from app.dependencies import get_db
from app.schemas.driver import DriverCreate, DriverResponse
from app.services.drivers.driver_service import (
    create_driver_service,
    get_driver_service,
)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/drivers", response_model=DriverResponse)
async def create_driver(driver: DriverCreate, db: AsyncSession = Depends(get_db)):
    return await create_driver_service(driver, db)


@router.get("/drivers/{driver_id}", response_model=DriverResponse)
async def get_driver(driver_id: int, db: AsyncSession = Depends(get_db)):
    return await get_driver_service(driver_id, db)
