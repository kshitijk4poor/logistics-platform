from datetime import timedelta

import aioredis
from app.config import settings
from app.dependencies import get_current_admin, get_current_user, get_db
from app.models import Role, User
from app.schemas.user import Token, UserCreate, UserResponse
from app.services.websocket_service import manager
from app.utils.auth import authenticate_user, create_access_token, get_password_hash
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

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


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(user_create: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user with the same email already exists
    result = await db.execute(select(User).where(User.email == user_create.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash the password
    hashed_password = get_password_hash(user_create.password)

    # Create new user
    new_user = User(
        name=user_create.name,
        email=user_create.email,
        phone_number=user_create.phone_number,
        password_hash=hashed_password,
        role_id=None,  # To be set based on role
    )

    # Assign role
    result = await db.execute(select(Role).where(Role.name == user_create.role))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=400, detail="Invalid role")
    new_user.role = role

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.post("/login", response_model=Token)
async def login_user(email: str, password: str, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id, "role": user.role.name},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}
