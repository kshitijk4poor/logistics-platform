import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from ..dependencies import get_current_user
from ..services.websocket_service import get_redis_connection, manager, publish_location

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


@router.websocket("/ws/users")
async def websocket_users(websocket: WebSocket, user=Depends(get_current_user)):
    # Implement authentication logic
    ...
    await manager.connect(websocket)
    redis = await get_redis_connection()
    try:
        pubsub = redis.pubsub()
        await pubsub.subscribe("driver_locations")
        async for message in pubsub.listen():
            if message["type"] == "message":
                await manager.send_personal_message(message["data"], websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        await pubsub.unsubscribe("driver_locations")
        await pubsub.close()


@router.websocket("/ws/drivers/batch")
async def websocket_drivers_batch(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if isinstance(data, list):
                for location in data:
                    driver_id = location.get("driver_id")
                    latitude = location.get("latitude")
                    longitude = location.get("longitude")
                    if driver_id and latitude and longitude:
                        await publish_location(driver_id, latitude, longitude)
            else:
                await websocket.send_text(
                    "Invalid data format. Expected a list of location updates."
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
