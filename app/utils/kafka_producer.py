import json

from app.services.messaging.kafka_service import kafka_service


async def publish_event(topic: str, event: dict):
    """
    Utility function to publish events to a specified Kafka topic.
    """
    try:
        message = json.dumps(event)
        await kafka_service.send_message(topic, event)
    except Exception as e:
        # Handle publishing errors, possibly log or retry
        print(f"Failed to publish event to {topic}: {e}")
