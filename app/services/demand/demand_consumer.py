import asyncio

from app.services.caching.cache import get_redis_client
from app.services.messaging.kafka_service import (KAFKA_TOPIC_DEMAND_UPDATES,
                                                  kafka_service)


async def handle_demand_update(demand_data):
    redis = await get_redis_client()
    h3_index = demand_data["h3_index"]
    demand = demand_data["demand"]

    # Update demand in Redis
    await redis.set(f"demand:{h3_index}", demand)
    await redis.expire(f"demand:{h3_index}", 3600)  # 1 hour


async def start_demand_consumer():
    await kafka_service.consume_messages(
        KAFKA_TOPIC_DEMAND_UPDATES, handle_demand_update
    )


if __name__ == "__main__":
    asyncio.run(start_demand_consumer())
