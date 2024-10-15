import asyncio

import aioredis

H3_INDEXES = ["8928308280fffff", "8928308283fffff"]  # Example H3 indices


async def update_demand():
    redis = await aioredis.from_url(
        "redis://localhost", encoding="utf-8", decode_responses=True
    )
    try:
        while True:
            for h3_index in H3_INDEXES:
                # Example logic: Demand increases with the number of active bookings in the area
                active_bookings = await redis.scard(f"active_bookings:{h3_index}")
                demand = 1.0 + (active_bookings * 0.1)  # Base demand is 1.0
                demand = min(demand, 2.5)  # Cap the demand
                await redis.set(f"demand:{h3_index}", demand)
            await asyncio.sleep(60)  # Update every minute
    finally:
        await redis.close()


# sample implementation of demand for surge pricing
