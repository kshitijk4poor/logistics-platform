import aioredis

REDIS_URL = "redis://localhost"


async def get_redis_client():
    return await aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)


async def cache_driver_availability(driver_id: int, is_available: bool):
    redis = await get_redis_client()
    await redis.set(f"driver:availability:{driver_id}", is_available)
    await redis.expire(f"driver:availability:{driver_id}", 3600)  # Cache for 1 hour


async def get_driver_availability(driver_id: int):
    redis = await get_redis_client()
    availability = await redis.get(f"driver:availability:{driver_id}")
    return availability == "True" if availability else None


async def cache_booking_status(booking_id: int, status: str):
    redis = await get_redis_client()
    await redis.set(f"booking:status:{booking_id}", status)
    await redis.expire(f"booking:status:{booking_id}", 3600)  # Cache for 1 hour


async def get_booking_status(booking_id: int):
    redis = await get_redis_client()
    status = await redis.get(f"booking:status:{booking_id}")
