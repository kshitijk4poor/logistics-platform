from unittest.mock import AsyncMock, patch

import pytest
from app.services.communication import WebSocketManager


@pytest.mark.asyncio
async def test_successful_user_connection():
    websocket = AsyncMock()
    token = "valid_user_token"
    with patch("app.services.websocket.authenticate_user", return_value=True):
        manager = WebSocketManager()
        await manager.connect(websocket, token)
        assert websocket in manager.active_connections


@pytest.mark.asyncio
async def test_successful_driver_connection():
    websocket = AsyncMock()
    token = "valid_driver_token"
    with patch("app.services.websocket.authenticate_driver", return_value=True):
        manager = WebSocketManager()
        await manager.connect(websocket, token)
        assert websocket in manager.active_connections


@pytest.mark.asyncio
async def test_connection_without_token():
    websocket = AsyncMock()
    token = None
    manager = WebSocketManager()
    with pytest.raises(ValueError):
        await manager.connect(websocket, token)


@pytest.mark.asyncio
async def test_connection_with_invalid_token():
    websocket = AsyncMock()
    token = "invalid_token"
    with patch("app.services.websocket.authenticate_user", return_value=False):
        manager = WebSocketManager()
        with pytest.raises(ValueError):
            await manager.connect(websocket, token)


@pytest.mark.asyncio
async def test_driver_connection_by_non_driver():
    websocket = AsyncMock()
    token = "non_driver_token"
    with patch("app.services.websocket.authenticate_driver", return_value=False):
        manager = WebSocketManager()
        with pytest.raises(ValueError):
            await manager.connect(websocket, token)


@pytest.mark.asyncio
async def test_successful_location_update():
    websocket = AsyncMock()
    location_data = {"latitude": 37.7749, "longitude": -122.4194}
    manager = WebSocketManager()
    await manager.receive_location_update(websocket, location_data)
    assert websocket in manager.active_connections


@pytest.mark.asyncio
async def test_unauthorized_location_update():
    websocket = AsyncMock()
    location_data = {"latitude": 37.7749, "longitude": -122.4194}
    manager = WebSocketManager()
    with pytest.raises(PermissionError):
        await manager.receive_location_update(websocket, location_data)


@pytest.mark.asyncio
async def test_malformed_location_data():
    websocket = AsyncMock()
    location_data = {"lat": 37.7749, "long": -122.4194}  # Incorrect keys
    manager = WebSocketManager()
    with pytest.raises(ValueError):
        await manager.receive_location_update(websocket, location_data)


@pytest.mark.asyncio
async def test_user_disconnection():
    websocket = AsyncMock()
    manager = WebSocketManager()
    manager.active_connections.add(websocket)
    await manager.disconnect(websocket)
    assert websocket not in manager.active_connections


@pytest.mark.asyncio
async def test_driver_unexpected_disconnection():
    websocket = AsyncMock()
    manager = WebSocketManager()
    manager.active_connections.add(websocket)
    await manager.disconnect(websocket)
    assert websocket not in manager.active_connections


@pytest.mark.asyncio
async def test_disconnect_without_authentication():
    websocket = AsyncMock()
    manager = WebSocketManager()
    await manager.disconnect(websocket)
    assert websocket not in manager.active_connections


@pytest.mark.asyncio
async def test_room_assignment():
    websocket = AsyncMock()
    room_id = "room_123"
    manager = WebSocketManager()
    await manager.assign_to_room(websocket, room_id)
    assert websocket in manager.rooms[room_id]


@pytest.mark.asyncio
async def test_message_broadcast():
    websocket = AsyncMock()
    room_id = "room_123"
    message = "Hello, room!"
    manager = WebSocketManager()
    manager.rooms[room_id] = {websocket}
    await manager.broadcast_to_room(room_id, message)
    websocket.send_text.assert_called_with(message)
