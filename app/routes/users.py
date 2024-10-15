import aioredis
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from app.dependencies import get_current_user
from app.services.websocket_service import manager

router = APIRouter()

REDIS_CHANNEL = "driver_locations"


@router.websocket("/ws/users")
async def websocket_users(websocket: WebSocket, current_user=Depends(get_current_user)):
    user_id = str(current_user.id)
    await manager.connect_user(user_id, websocket)
    redis = await aioredis.from_url(
        "redis://localhost", encoding="utf-8", decode_responses=True
    )
    try:
        pubsub = redis.pubsub()
        await pubsub.subscribe(REDIS_CHANNEL)
        async for message in pubsub.listen():
            if message["type"] == "message":
                await manager.send_personal_message(message["data"], websocket)
    except WebSocketDisconnect:
        await manager.disconnect_user(user_id)
    except Exception as e:
        await manager.send_personal_message(f"Error: {str(e)}", websocket)
        await manager.disconnect_user(user_id)
    finally:
        await pubsub.unsubscribe(REDIS_CHANNEL)
        await pubsub.close()
