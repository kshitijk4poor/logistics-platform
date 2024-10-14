import json
import time
from typing import Dict

import aioredis
from fastapi import Depends, WebSocket, WebSocketDisconnect

from .tracking import REDIS_URL


class ConnectionManager:
    def __init__(self):
        self.active_drivers: Dict[str, WebSocket] = {}
        self.active_users: Dict[str, WebSocket] = {}

    async def connect_driver(self, driver_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_drivers[driver_id] = websocket

    async def disconnect_driver(self, driver_id: str):
        self.active_drivers.pop(driver_id, None)

    async def connect_user(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_users[user_id] = websocket

    async def disconnect_user(self, user_id: str):
        self.active_users.pop(user_id, None)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_to_users(self, message: str):
        for connection in self.active_users.values():
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
