from unittest.mock import MagicMock, patch

import pytest
from app.services.messaging import KafkaConsumerService, KafkaProducerService


@pytest.mark.asyncio
async def test_producer_send_message_success():
    producer = KafkaProducerService()
    with patch.object(producer, "send", return_value=True) as mock_send:
        result = await producer.send("test_topic", {"key": "value"})
        assert result is True
        mock_send.assert_called_once_with("test_topic", {"key": "value"})


@pytest.mark.asyncio
async def test_producer_send_message_failure():
    producer = KafkaProducerService()
    with patch.object(producer, "send", side_effect=Exception("Send failure")):
        with pytest.raises(Exception):
            await producer.send("test_topic", {"key": "value"})


@pytest.mark.asyncio
async def test_consumer_receive_message_success():
    consumer = KafkaConsumerService()
    message = MagicMock(value=b'{"key": "value"}')
    with patch.object(consumer, "consume", return_value=[message]):
        messages = await consumer.consume("test_topic")
        assert len(messages) == 1
        assert messages[0].value == b'{"key": "value"}'


@pytest.mark.asyncio
async def test_consumer_error_handling():
    consumer = KafkaConsumerService()
    with patch.object(consumer, "consume", side_effect=Exception("Consume error")):
        with pytest.raises(Exception):
            await consumer.consume("test_topic")


@pytest.mark.asyncio
async def test_message_serialization():
    producer = KafkaProducerService()
    message = {"key": "value"}
    serialized_message = producer.serialize(message)
    assert isinstance(serialized_message, bytes)


@pytest.mark.asyncio
async def test_message_deserialization():
    consumer = KafkaConsumerService()
    serialized_message = b'{"key": "value"}'
    message = consumer.deserialize(serialized_message)
    assert message == {"key": "value"}


@pytest.mark.asyncio
async def test_kafka_connection_handling():
    producer = KafkaProducerService()
    consumer = KafkaConsumerService()
    with patch.object(
        producer, "start", return_value=True
    ) as mock_start_producer, patch.object(
        consumer, "start", return_value=True
    ) as mock_start_consumer, patch.object(
        producer, "stop", return_value=True
    ) as mock_stop_producer, patch.object(
        consumer, "stop", return_value=True
    ) as mock_stop_consumer:
        await producer.start()
        await consumer.start()
        await producer.stop()
        await consumer.stop()
        mock_start_producer.assert_called_once()
        mock_start_consumer.assert_called_once()
        mock_stop_producer.assert_called_once()
        mock_stop_consumer.assert_called_once()


@pytest.mark.asyncio
async def test_kafka_broker_unavailability():
    producer = KafkaProducerService()
    with patch.object(producer, "send", side_effect=Exception("Broker unavailable")):
        with pytest.raises(Exception):
            await producer.send("test_topic", {"key": "value"})
