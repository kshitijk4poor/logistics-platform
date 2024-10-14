import json
from typing import List

import aioredis
from fastapi import Depends, WebSocket, WebSocketDisconnect

from .tracking import REDIS_URL


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


async def get_redis_connection():
    return await aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)


async def publish_location(driver_id: int, latitude: float, longitude: float):
    redis = await get_redis_connection()
    location_data = json.dumps(
        {
            "driver_id": driver_id,
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": int(time.time()),
        }
    )
    await redis.publish("driver_locations", location_data)
