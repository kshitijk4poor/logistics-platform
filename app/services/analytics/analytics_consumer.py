import asyncio
import json

from app.services.analytics.analytics_service import create_analytics_service
from app.services.messaging.kafka_service import (
    KAFKA_TOPIC_ANALYTICS_UPDATES, kafka_service)


async def handle_analytics_update(message):
    """
    Process analytics updates from Kafka.
    """
    try:
        data = json.loads(message.value)
        await create_analytics_service(data)

    except Exception as e:
        print(f"Error processing analytics update: {e}")


async def start_analytics_consumer():
    await kafka_service.consume_messages(
        KAFKA_TOPIC_ANALYTICS_UPDATES, handle_analytics_update
    )
