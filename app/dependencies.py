import json
import time
from functools import wraps

import aioredis
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.models import Admin
from db.database import get_db

redis = aioredis.from_url(
    "redis://localhost", decode_responses=True, max_connections=10
)


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


async def get_current_admin(
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
    admin = db.query(Admin).filter(Admin.username == username).first()
    if admin is None:
        raise credentials_exception
    return admin


def rate_limit(max_calls: int, time_frame: int):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = args[0]
            key = f"rate_limit:{func.__name__}:{request.client.host}"
            if await rate_limiter.is_rate_limited(key, max_calls, time_frame):
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            return await func(*args, **kwargs)

        return wrapper

    return decorator
