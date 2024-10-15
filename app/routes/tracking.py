import h3
from fastapi import APIRouter, Depends, Security, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.dependencies import get_current_driver, get_current_user
from app.models import Driver, User
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
    await manager.connect_driver(driver_id, websocket)
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
                await manager.update_driver_location(
                    driver_id, lat, lng, vehicle_type, is_available
                )
            except Exception as e:
                await websocket.send_text(f"Error processing data: {e}")
    except WebSocketDisconnect:
        await manager.disconnect_driver(driver_id)


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
    nearby_drivers = []
    current_radius = initial_radius_km

    while current_radius <= max_radius_km and not nearby_drivers:
        h3_index = h3.geo_to_h3(lat, lng, manager.h3_resolution)
        search_indexes = h3.k_ring(
            h3_index, int(current_radius / manager.h3_ring_distance)
        )

        for index in search_indexes:
            drivers = manager.h3_index_to_drivers.get(index, [])
            for driver_id in drivers:
                driver_info = manager.driver_locations.get(driver_id)
                if driver_info and (
                    vehicle_type.lower() == "all"
                    or driver_info["vehicle_type"] == vehicle_type
                ):
                    nearby_drivers.append(
                        {
                            "driver_id": driver_id,
                            "location": driver_info["h3_index"],
                            "vehicle_type": driver_info["vehicle_type"],
                        }
                    )

        if not nearby_drivers:
            current_radius *= 2  # Double the radius for the next iteration

    return {"nearby_drivers": nearby_drivers, "search_radius_km": current_radius}
