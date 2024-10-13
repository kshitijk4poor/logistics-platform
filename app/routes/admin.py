from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_current_admin
from app.models import Vehicle
from app.schemas.vehicles import VehicleResponse, VehicleSchema
from db.database import get_db

router = APIRouter()


@router.get(
    "/admin/fleet",
    dependencies=[Depends(get_current_admin)],
    response_model=List[VehicleResponse],
)
async def get_fleet(db: Session = Depends(get_db)):
    vehicles = db.query(Vehicle).all()
    return vehicles


@router.post("/admin/fleet", dependencies=[Depends(get_current_admin)])
async def add_vehicle(vehicle_data: VehicleSchema, db: Session = Depends(get_db)):
    vehicle = Vehicle(**vehicle_data.dict())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle
