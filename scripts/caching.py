import aioredis
import json

redis = aioredis.from_url(
    "redis://localhost",
    decode_responses=True,
    max_connections=10
)


class Cache:
    async def get(self, key):
        value = await redis.get(key)
        return json.loads(value) if value else None

    async def set(self, key, value, expire=None):
        serialized_value = json.dumps(value)
        await redis.set(key, serialized_value, ex=expire)


cache = Cache()