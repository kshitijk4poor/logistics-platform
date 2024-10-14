from typing import Dict, List, Union

import h3
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordBearer, Security
from sqlalchemy.orm import Session

from app.dependencies import get_current_driver, get_current_user
from app.models import Booking, BookingStatusEnum, Driver, User
from app.schemas.booking import BookingAssignment, StatusUpdateRequest
from app.services.websocket_service import ConnectionManager
from db.database import get_db

router = APIRouter()

manager = ConnectionManager()


@router.websocket("/ws/{driver_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    driver_id: str,
    current_driver: Driver = Security(get_current_driver, scopes=["driver"]),
    db: Session = Depends(get_db),
):
    if str(current_driver.id) != driver_id:
        await websocket.close(code=4003)
        return
    token = websocket.query_params.get("token")
    if not verify_token(token, driver_id):
        await websocket.close(code=1008)
        return
    await manager.connect(websocket, driver_id)
    try:
        while True:
            try:
                data = await websocket.receive_json()
                lat = data.get("latitude")
                lng = data.get("longitude")
                vehicle_type = data.get("vehicle_type")
                is_available = data.get("is_available")
                if not all([lat, lng, vehicle_type, is_available]):
                    await websocket.send_text("Invalid data format.")
                    continue
                manager.update_driver_location(
                    driver_id, lat, lng, vehicle_type, is_available
                )
                # Optionally broadcast location updates
                await manager.broadcast(
                    f"Driver {driver_id} updated location: {lat}, {lng}"
                )
            except Exception as e:
                await websocket.send_text(f"Error processing data: {e}")
    except WebSocketDisconnect:
        manager.disconnect(driver_id)


@router.get("/nearby-drivers")
async def get_nearby_drivers(
    lat: float,
    lng: float,
    radius_km: float = 5,
    vehicle_type: str = "all",
    current_user: User = Security(get_current_user, scopes=["user"]),
    db: Session = Depends(get_db),
):
    if vehicle_type.lower() != "all":
        # Filter by vehicle_type
        nearby_drivers = [
            {
                "driver_id": id,
                "location": manager.driver_locations[id]["h3_index"],
                "vehicle_type": manager.driver_locations[id]["vehicle_type"],
            }
            for id in manager.get_nearby_drivers(lat, lng, radius_km, vehicle_type)
        ]
    else:
        nearby_drivers = [
            {
                "driver_id": id,
                "location": manager.driver_locations[id]["h3_index"],
                "vehicle_type": manager.driver_locations[id]["vehicle_type"],
            }
            for id in manager.get_nearby_drivers(lat, lng, radius_km, "all")
        ]
    return {"nearby_drivers": nearby_drivers}
