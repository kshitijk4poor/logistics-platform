import json
import time
from typing import Any, Dict, List

import aioredis
import h3

from .driver_tracking import DriverTracker

REDIS_URL = "redis://localhost"


async def get_redis_client() -> aioredis.Redis:
    return await aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)


async def update_driver_locations(driver_updates: List[Dict[str, Any]]):
    """
    Update multiple drivers' locations in Redis and maintain H3 index sets.
    """
    redis = await get_redis_client()
    pipeline = redis.pipeline()

    for update in driver_updates:
        driver_id = update["driver_id"]
        latitude = update["latitude"]
        longitude = update["longitude"]
        vehicle_type = update["vehicle_type"]

        # Update driver's location
        location_key = f"driver:location:{driver_id}"
        location_data = json.dumps(
            {"lat": latitude, "lng": longitude, "timestamp": int(time.time())}
        )
        pipeline.set(location_key, location_data)

        # Update H3 index sets
        h3_index = h3.geo_to_h3(latitude, longitude, 9)  # Adjust resolution as needed

        # Remove driver from old H3 index set (if exists)
        old_h3_index = await redis.get(f"driver:h3:{driver_id}")
        if old_h3_index:
            pipeline.srem(f"drivers:{old_h3_index}:{vehicle_type}", driver_id)

        # Add driver to new H3 index set
        pipeline.sadd(f"drivers:{h3_index}:{vehicle_type}", driver_id)
        pipeline.set(f"driver:h3:{driver_id}", h3_index)

        # Set expiration for all keys
        pipeline.expire(location_key, 300)  # 5 minutes
        pipeline.expire(f"drivers:{h3_index}:{vehicle_type}", 300)
        pipeline.expire(f"driver:h3:{driver_id}", 300)

    # Execute all Redis commands in a single batch
    await pipeline.execute()
