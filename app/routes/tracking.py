from typing import Dict, List, Union

import h3
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordBearer, Security
from sqlalchemy.orm import Session

from app.dependencies import get_current_driver, get_current_user
from db.database import get_db

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.driver_locations: Dict[str, Dict[str, Union[str, float, bool]]] = {}

    async def connect(self, websocket: WebSocket, driver_id: str):
        await websocket.accept()
        self.active_connections[driver_id] = websocket

    def disconnect(self, driver_id: str):
        self.active_connections.pop(driver_id, None)
        self.driver_locations.pop(driver_id, None)

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

    def update_driver_location(
        self,
        driver_id: str,
        lat: float,
        lng: float,
        vehicle_type: str,
        is_available: bool,
    ):
        h3_index = h3.geo_to_h3(lat, lng, 9)  # Resolution 9 for ~150m precision
        self.driver_locations[driver_id] = {
            "h3_index": h3_index,
            "lat": lat,
            "lng": lng,
            "vehicle_type": vehicle_type,
            "is_available": is_available,
        }

    def get_nearby_drivers(
        self, lat: float, lng: float, radius_km: float, vehicle_type: str
    ) -> List[str]:
        center_index = h3.geo_to_h3(lat, lng, 9)
        search_indexes = h3.k_ring(
            center_index, int(radius_km / 0.15)
        )  # Approximate km to resolution 9 hexagons
        nearby_drivers = [
            driver_id
            for driver_id, info in self.driver_locations.items()
            if info["h3_index"] in search_indexes
            and info["vehicle_type"] == vehicle_type
            and info["is_available"]
        ]
        return nearby_drivers


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
    # Implement authentication logic
    token = websocket.query_params.get("token")
    if not verify_token(token, driver_id):
        await websocket.close(code=1008)
        return
    # Proceed with connection
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
                # Proceed with processing
            except Exception as e:
                await websocket.send_text(f"Error processing data: {e}")
            manager.update_driver_location(
                driver_id, lat, lng, vehicle_type, is_available
            )
            await manager.broadcast(
                f"Driver {driver_id} updated location: {lat}, {lng}"
            )
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
                "location": info["h3_index"],
                "vehicle_type": info["vehicle_type"],
            }
            for id in manager.get_nearby_drivers(lat, lng, radius_km, vehicle_type)
        ]
    else:
        nearby_drivers = [
            {
                "driver_id": id,
                "location": info["h3_index"],
                "vehicle_type": info["vehicle_type"],
            }
            for id in manager.get_nearby_drivers(lat, lng, radius_km, "all")
        ]
    return {"nearby_drivers": nearby_drivers}
