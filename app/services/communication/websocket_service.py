import asyncio
import json
from typing import Dict, List, Set

import h3
from fastapi import WebSocket

from .tracking import driver_tracker


class ConnectionManager:
    def __init__(self):
        self.active_users: Dict[str, WebSocket] = {}
        self.active_drivers: Dict[str, WebSocket] = {}
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
        # Delegate to DriverTracker
        driver_tracker.add_location_update(driver_id, lat, lng, vehicle_type)

    async def process_booking_assignment(self, booking):
        message = json.dumps(
            {
                "type": "assignment",
                "data": {
                    "booking_id": booking.id,
                    "message": "You have been assigned a new booking.",
                },
            }
        )
        await self.send_message_to_driver(str(booking.driver_id), message)


manager = ConnectionManager()

# Start the batch processing task
asyncio.create_task(manager.start_batch_processing())
