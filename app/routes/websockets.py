import logging

from fastapi import APIRouter, WebSocket
from opentelemetry import trace

from app.services.communication.websocket_service import (
    handle_driver_batch_connection,
    handle_driver_connection,
    handle_user_connection,
)

router = APIRouter()

tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)


@router.websocket("/ws/drivers")
async def websocket_drivers(websocket: WebSocket):
    with tracer.start_as_current_span("websocket_drivers"):
        await handle_driver_connection(websocket)


@router.websocket("/ws/users")
async def websocket_users(websocket: WebSocket):
    with tracer.start_as_current_span("websocket_users"):
        await handle_user_connection(websocket)


@router.websocket("/ws/drivers/batch")
async def websocket_drivers_batch(websocket: WebSocket):
    with tracer.start_as_current_span("websocket_drivers_batch"):
        await handle_driver_batch_connection(websocket)
