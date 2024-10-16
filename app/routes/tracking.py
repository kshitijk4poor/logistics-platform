import logging

import h3
from fastapi import (APIRouter, Depends, Security, WebSocket,
                     WebSocketDisconnect)
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.dependencies import get_current_driver, get_current_user
from app.models import Driver, User
from app.services.communication.websocket_service import ConnectionManager
from app.services.tracking.tracking_service import TrackingService
from db.database import get_db

router = APIRouter()

manager = ConnectionManager()
tracking_service = TrackingService(manager)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@router.websocket("/ws/{driver_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    driver_id: str,
    current_driver: Driver = Security(get_current_driver, scopes=["driver"]),
    db: Session = Depends(get_db),
):
    await tracking_service.websocket_connection(
        websocket, driver_id, current_driver, db
    )


@router.get("/nearby-drivers")
async def get_nearby_drivers(
    lat: float,
    lng: float,
    initial_radius_km: float = 1,
    max_radius_km: float = 10,
    vehicle_type: str = "all",
    current_user: User = Security(get_current_user, scopes=["user"]),
    db: Session = Depends(get_db),
):
    nearby_drivers = await tracking_service.get_nearby_drivers(
        lat, lng, initial_radius_km, max_radius_km, vehicle_type
    )
    return nearby_drivers


async def get_current_user_object(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    return await get_current_user(token, db)
