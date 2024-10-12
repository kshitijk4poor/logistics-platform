import time
from functools import wraps

from fastapi import HTTPException


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