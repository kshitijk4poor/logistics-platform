import asyncio
import time
from typing import Any, Dict

from app.services.messaging.kafka_service import kafka_service

KAFKA_TOPIC_DEMAND_UPDATES = "demand_updates"
H3_INDEXES = ["8928308280fffff", "8928308283fffff"]  # Example H3 indices


async def update_demand():
    while True:
        for h3_index in H3_INDEXES:
            # Example logic: Demand increases with time (replace with actual logic)
            demand = (
                1.0 + (time.time() % 3600) / 3600
            )  # Base demand is 1.0, increases over an hour
            demand = min(demand, 2.5)  # Cap the demand

            demand_data: Dict[str, Any] = {
                "h3_index": h3_index,
                "demand": demand,
                "timestamp": int(time.time()),
            }

            # Publish demand update to Kafka
            await kafka_service.send_message(KAFKA_TOPIC_DEMAND_UPDATES, demand_data)

        await asyncio.sleep(60)  # Update every minute


# Run this function in a separate process or thread
if __name__ == "__main__":
    asyncio.run(update_demand())
