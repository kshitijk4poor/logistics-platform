import json
import time
from functools import wraps

import aioredis
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseSettings
from sqlalchemy.orm import Session

from app.models import Admin, Driver, Role, RoleEnum, User
from db.database import get_db

redis = aioredis.from_url(
    "redis://localhost", decode_responses=True, max_connections=10
)


class Settings(BaseSettings):
    SECRET_KEY: str = "your_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


settings = Settings()


class Cache:
    async def get(self, key):
        value = await redis.get(key)
        return json.loads(value) if value else None

    async def set(self, key, value, expire=None):
        serialized_value = json.dumps(value)
        await redis.set(key, serialized_value, ex=expire)


cache = Cache()


class RateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def is_rate_limited(self, key, max_calls, time_frame):
        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, time_frame)
        if current > max_calls:
            return True
        return False


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == username).first()
    if user is None:
        raise credentials_exception
    return user


async def has_role(required_role: RoleEnum):
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role.name != required_role:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return role_checker


get_current_admin = has_role(RoleEnum.admin)
get_current_driver = has_role(RoleEnum.driver)


async def get_current_driver_object(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    driver = db.query(Driver).filter(Driver.id == user_id).first()
    if driver is None:
        raise credentials_exception
    return driver


def rate_limit(max_calls: int, time_frame: int):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request") or args[0]
            client_ip = request.client.host
            key = f"rate_limit:{func.__name__}:{client_ip}"

            rate_limiter = RateLimiter(redis)

            if await rate_limiter.is_rate_limited(key, max_calls, time_frame):
                raise HTTPException(status_code=429, detail="Rate limit exceeded")

            return await func(*args, **kwargs)

        return wrapper

    return decorator
