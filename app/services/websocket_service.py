import asyncio
import json
import time
from typing import Dict, Set, List

import aioredis
import h3
from fastapi import WebSocket

from .tracking import REDIS_URL, update_driver_locations


class ConnectionManager:
    def __init__(self):
        self.active_users: Dict[str, WebSocket] = {}
        self.active_drivers: Dict[str, WebSocket] = {}
        self.location_update_queue: List[Dict] = []
        self.batch_size = 10
        self.h3_resolution = 9
        self.h3_ring_distance = 1
        self.h3_index_to_drivers: Dict[str, Set[str]] = {}
        self.driver_locations: Dict[str, Dict] = {}
        self.batch_update_interval = 5  # seconds

    async def connect_user(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_users[user_id] = websocket

    async def connect_driver(self, driver_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_drivers[driver_id] = websocket

    async def disconnect_user(self, user_id: str):
        self.active_users.pop(user_id, None)

    async def disconnect_driver(self, driver_id: str):
        self.active_drivers.pop(driver_id, None)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_to_users(self, message: str):
        for connection in self.active_users.values():
            await connection.send_text(message)

    async def send_message_to_driver(self, driver_id: str, message: str):
        if driver_id in self.active_drivers:
            await self.active_drivers[driver_id].send_text(message)

    async def update_driver_location(
        self,
        driver_id: str,
        lat: float,
        lng: float,
        vehicle_type: str,
        is_available: bool,
    ):
        self.location_update_queue.append(
            {
                "driver_id": driver_id,
                "latitude": lat,
                "longitude": lng,
                "vehicle_type": vehicle_type,
                "is_available": is_available,
            }
        )

        if len(self.location_update_queue) >= self.batch_size:
            await self.process_batch_updates()

    async def process_batch_updates(self):
        if not self.location_update_queue:
            return

        updates_to_process = self.location_update_queue[: self.batch_size]
        self.location_update_queue = self.location_update_queue[self.batch_size :]

        await update_driver_locations(updates_to_process)

        for update in updates_to_process:
            driver_id = update["driver_id"]
            new_h3_index = h3.geo_to_h3(
                update["latitude"], update["longitude"], self.h3_resolution
            )

            old_h3_index = self.driver_locations.get(driver_id, {}).get("h3_index")
            if old_h3_index and old_h3_index != new_h3_index:
                self.h3_index_to_drivers[old_h3_index].remove(driver_id)
                if not self.h3_index_to_drivers[old_h3_index]:
                    del self.h3_index_to_drivers[old_h3_index]

            if new_h3_index not in self.h3_index_to_drivers:
                self.h3_index_to_drivers[new_h3_index] = set()
            self.h3_index_to_drivers[new_h3_index].add(driver_id)

            self.driver_locations[driver_id] = {
                "h3_index": new_h3_index,
                "vehicle_type": update["vehicle_type"],
                "is_available": update["is_available"],
            }

    async def start_batch_processing(self):
        while True:
            await asyncio.sleep(self.batch_update_interval)
            await self.process_batch_updates()


manager = ConnectionManager()

# Start the batch processing task
asyncio.create_task(manager.start_batch_processing())


async def get_redis_connection():
    return await aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)


async def publish_location(
    driver_id: int, latitude: float, longitude: float, assignment: Dict = None
):
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

    # Send assignment notification to driver if provided
    if assignment:
        assignment_message = json.dumps({"type": "assignment", "data": assignment})
        await manager.send_message_to_driver(str(driver_id), assignment_message)