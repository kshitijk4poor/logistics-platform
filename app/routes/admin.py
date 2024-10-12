from fastapi import APIRouter, Depends
from app.schemas.vehicle import VehicleSchema, VehicleResponse
from app.dependencies import get_current_admin
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from app.database import get_db
from app.models import Vehicle
from typing import List



router = APIRouter()

@router.get("/admin/fleet", dependencies=[Depends(get_current_admin)], response_model=List[VehicleResponse])
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