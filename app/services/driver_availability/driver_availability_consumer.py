import asyncio
import json

from app.services.caching.cache import cache_driver_availability
from app.services.messaging.kafka_service import (
    KAFKA_TOPIC_DRIVER_AVAILABILITY_UPDATES, kafka_service)


async def handle_driver_availability_update(message):
    """
    Process driver availability updates from Kafka with retry logic.
    """
    retry_count = 0
    max_retries = 5
    while retry_count < max_retries:
        try:
            data = json.loads(message.value)
            driver_id = data["driver_id"]
            is_available = data["is_available"]

            # Update availability in cache or database
            await cache_driver_availability(driver_id, is_available)
            break  # Exit loop if successful

        except Exception as e:
            retry_count += 1
            print(
                f"Error processing driver availability update: {e}. Retry {retry_count}/{max_retries}"
            )
            await asyncio.sleep(2**retry_count)  # Exponential backoff

    if retry_count == max_retries:
        print(
            f"Failed to process driver availability update after {max_retries} attempts."
        )


async def start_driver_availability_consumer():
    await kafka_service.consume_messages(
        KAFKA_TOPIC_DRIVER_AVAILABILITY_UPDATES, handle_driver_availability_update
    )
