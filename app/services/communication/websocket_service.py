import asyncio
import json
from typing import Dict, List, Set

from fastapi import WebSocket, status, WebSocketDisconnect
from pydantic import ValidationError
import h3
from app.services.tracking import driver_tracker
from app.services.tracking.tracking_service import TrackingService
from app.dependencies import get_current_user
from app.services.caching.cache import get_redis_client
from circuitbreaker import circuit
import logging
from opentelemetry import trace

from app.models import LocationUpdate

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

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
        self.tracking_service = TrackingService(self)

        # Start the batch processing task
        asyncio.create_task(self.start_batch_processing())

    async def connect_user(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_users[user_id] = websocket
        logger.info(f"User {user_id} connected.")

    async def connect_driver(self, driver_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_drivers[driver_id] = websocket
        logger.info(f"Driver {driver_id} connected.")

    async def disconnect_user(self, user_id: str):
        self.active_users.pop(user_id, None)
        logger.info(f"User {user_id} disconnected.")

    async def disconnect_driver(self, driver_id: str):
        self.active_drivers.pop(driver_id, None)
        logger.info(f"Driver {driver_id} disconnected.")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
        logger.debug(f"Sent personal message: {message}")

    async def broadcast_to_users(self, message: str):
        for connection in self.active_users.values():
            await connection.send_text(message)
        logger.debug(f"Broadcasted message to all users: {message}")

    async def send_message_to_driver(self, driver_id: str, message: str):
        websocket = self.active_drivers.get(driver_id)
        if websocket:
            await websocket.send_text(message)
            logger.debug(f"Sent message to driver {driver_id}: {message}")

    async def update_driver_location(
        self,
        driver_id: str,
        lat: float,
        lng: float,
        vehicle_type: str,
        is_available: bool,
    ):
        # Delegate to TrackingService
        await self.tracking_service.update_driver_location(
            driver_id, lat, lng, vehicle_type, is_available
        )

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
        logger.info(f"Processed booking assignment for driver {booking.driver_id}")

    async def start_batch_processing(self):
        while True:
            await asyncio.sleep(self.batch_update_interval)
            await self.process_batch_updates()

    async def process_batch_updates(self):
        updates = driver_tracker.get_batch_updates(self.batch_size)
        if updates:
            await driver_tracker.process_batch_updates(updates)
            logger.debug(f"Processed batch updates: {updates}")

manager = ConnectionManager()

tracking_service = TrackingService(manager)

@circuit(failure_threshold=5, recovery_timeout=30)
async def get_redis_connection_with_circuit_breaker():
    return await get_redis_client()

async def authenticate_websocket(websocket: WebSocket, is_driver: bool = False):
    token = websocket.headers.get("Authorization")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning("WebSocket connection closed due to missing token.")
        return None

    try:
        token_type, token_value = token.split()
        if token_type.lower() != "bearer":
            raise ValueError("Invalid token type")
        user = await get_current_user(token_value)
        if not user:
            raise ValueError("Invalid token")
        if is_driver and not user.get("is_driver"):
            raise ValueError("User is not a driver")
        logger.info(f"Authenticated {'driver' if is_driver else 'user'}: {user['id']}")
        return user
    except (ValueError, IndexError) as e:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning(f"WebSocket connection closed due to authentication error: {e}")
        return None

async def handle_driver_connection(websocket: WebSocket):
    user = await authenticate_websocket(websocket, is_driver=True)
    if not user:
        return

    driver_id = str(user['id'])
    await manager.connect_driver(driver_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                location = LocationUpdate.parse_raw(data)
                await manager.update_driver_location(
                    location.driver_id,
                    location.latitude,
                    location.longitude,
                    user["vehicle_type"],
                    user["is_available"]
                )
            except ValidationError as e:
                error_message = f"Invalid data format: {str(e)}"
                await manager.send_personal_message(error_message, websocket)
                logger.error(f"Validation error from driver {driver_id}: {e}")
    except WebSocketDisconnect:
        await manager.disconnect_driver(driver_id)
    except Exception as e:
        logger.error(f"Error in handle_driver_connection: {str(e)}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)

async def handle_user_connection(websocket: WebSocket):
    user = await authenticate_websocket(websocket)
    if not user:
        return

    user_id = str(user['id'])
    await manager.connect_user(user_id, websocket)
    try:
        redis = await get_redis_client()
        pubsub = redis.pubsub()
        await pubsub.subscribe("driver_locations")
        logger.info(f"User {user_id} subscribed to 'driver_locations' channel.")
        async for message in pubsub.listen():
            if message["type"] == "message":
                await manager.send_personal_message(message["data"], websocket)
    except WebSocketDisconnect:
        await manager.disconnect_user(user_id)
    except Exception as e:
        logger.error(f"Error in handle_user_connection: {str(e)}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
    finally:
        await pubsub.unsubscribe("driver_locations")
        await pubsub.close()
        logger.info(f"User {user_id} unsubscribed and connection closed.")

async def handle_driver_batch_connection(websocket: WebSocket):
    user = await authenticate_websocket(websocket, is_driver=True)
    if not user:
        return

    driver_id = str(user['id'])
    await manager.connect_driver(driver_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if isinstance(data, list):
                for location in data:
                    try:
                        location_update = LocationUpdate(**location)
                        await manager.update_driver_location(
                            location_update.driver_id,
                            location_update.latitude,
                            location_update.longitude,
                            user["vehicle_type"],
                            user["is_available"]
                        )
                    except ValidationError as e:
                        error_message = f"Invalid data format: {str(e)}"
                        await manager.send_personal_message(error_message, websocket)
                        logger.error(f"Batch validation error from driver {driver_id}: {e}")
            else:
                error_message = "Invalid data format. Expected a list of location updates."
                await manager.send_personal_message(error_message, websocket)
                logger.warning(f"Driver {driver_id} sent invalid batch data.")
    except WebSocketDisconnect:
        await manager.disconnect_driver(driver_id)
    except Exception as e:
        logger.error(f"Error in handle_driver_batch_connection: {str(e)}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
