from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import json
from app.config import settings

class KafkaService:
    def __init__(self):
        self.producer = None
        self.consumer = None

    async def start(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_URL,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await self.producer.start()

    async def stop(self):
        if self.producer:
            await self.producer.stop()
        if self.consumer:
            await self.consumer.stop()

    async def send_message(self, topic, message):
        await self.producer.send_and_wait(topic, message)

    async def consume_messages(self, topic, message_handler):
        self.consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=settings.KAFKA_URL,
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        await self.consumer.start()
        try:
            async for msg in self.consumer:
                await message_handler(msg.value)
        finally:
            await self.consumer.stop()

kafka_service = KafkaService()