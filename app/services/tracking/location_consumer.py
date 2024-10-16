import asyncio
import json
from app.services.messaging.kafka_service import kafka_service
from app.services.caching.cache import get_redis_client

KAFKA_TOPIC_DRIVER_LOCATIONS = "driver_locations"

async def handle_location_update(location_data):
    redis = await get_redis_client()
    driver_id = location_data["driver_id"]
    h3_index = location_data["h3_index"]
    vehicle_type = location_data["vehicle_type"]

    # Update driver's location
    location_key = f"driver:location:{driver_id}"
    await redis.set(location_key, json.dumps(location_data))
    await redis.expire(location_key, 300)  # 5 minutes

    # Update H3 index sets
    await redis.sadd(f"drivers:{h3_index}:{vehicle_type}", driver_id)
    await redis.expire(f"drivers:{h3_index}:{vehicle_type}", 300)

    await redis.set(f"driver:h3:{driver_id}", h3_index)
    await redis.expire(f"driver:h3:{driver_id}", 300)

async def start_location_consumer():
    await kafka_service.consume_messages(KAFKA_TOPIC_DRIVER_LOCATIONS, handle_location_update)

# Run this function in a separate process or thread
if __name__ == "__main__":
    asyncio.run(start_location_consumer())