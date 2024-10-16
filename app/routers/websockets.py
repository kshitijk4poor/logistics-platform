import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.websocket_service import manager, publish_location

router = APIRouter()


@router.websocket("/ws/drivers")
async def websocket_drivers(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            location = json.loads(data)
            driver_id = location.get("driver_id")
            latitude = location.get("latitude")
            longitude = location.get("longitude")
            if driver_id and latitude and longitude:
                await publish_location(driver_id, latitude, longitude)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
