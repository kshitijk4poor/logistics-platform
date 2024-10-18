from unittest.mock import MagicMock, patch

import pytest
from app.services.analytics import AnalyticsConsumer
from app.services.demand import DemandConsumer


@pytest.fixture
def analytics_consumer():
    return AnalyticsConsumer()


@pytest.fixture
def demand_consumer():
    return DemandConsumer()


@pytest.mark.asyncio
async def test_analytics_update_handling_success(analytics_consumer):
    analytics_data = {"metric": "rides", "value": 100}
    with patch.object(
        analytics_consumer, "process_analytics", return_value=True
    ) as mock_process:
        result = await analytics_consumer.process_analytics(analytics_data)
        assert result is True
        mock_process.assert_called_once_with(analytics_data)


@pytest.mark.asyncio
async def test_analytics_update_handling_malformed_data(analytics_consumer):
    analytics_data = {"metric": "rides"}  # Missing 'value'
    with pytest.raises(KeyError):
        await analytics_consumer.process_analytics(analytics_data)


@pytest.mark.asyncio
async def test_analytics_update_handling_duplicates(analytics_consumer):
    analytics_data = {"metric": "rides", "value": 100}
    with patch.object(
        analytics_consumer, "process_analytics", return_value=False
    ) as mock_process:
        result = await analytics_consumer.process_analytics(analytics_data)
        assert result is False


@pytest.mark.asyncio
async def test_demand_update_handling_success(demand_consumer):
    demand_data = {"location": "city_center", "demand": 50}
    with patch.object(
        demand_consumer, "update_demand_cache", return_value=True
    ) as mock_update:
        result = await demand_consumer.update_demand_cache(demand_data)
        assert result is True
        mock_update.assert_called_once_with(demand_data)


@pytest.mark.asyncio
async def test_demand_update_handling_malformed_data(demand_consumer):
    demand_data = {"location": "city_center"}  # Missing 'demand'
    with pytest.raises(KeyError):
        await demand_consumer.update_demand_cache(demand_data)


@pytest.mark.asyncio
async def test_demand_data_expiration(demand_consumer):
    demand_data = {"location": "city_center", "demand": 50}
    with patch.object(
        demand_consumer, "set_cache_expiration", return_value=True
    ) as mock_set_expiration:
        await demand_consumer.update_demand_cache(demand_data)
        mock_set_expiration.assert_called_once()


@pytest.mark.asyncio
async def test_consumer_operations_success(analytics_consumer, demand_consumer):
    message = MagicMock(value=b'{"metric": "rides", "value": 100}')
    with patch.object(
        analytics_consumer, "consume", return_value=[message]
    ), patch.object(demand_consumer, "consume", return_value=[message]):
        analytics_messages = await analytics_consumer.consume("analytics_topic")
        demand_messages = await demand_consumer.consume("demand_topic")
        assert len(analytics_messages) == 1
        assert len(demand_messages) == 1


@pytest.mark.asyncio
async def test_consumer_message_processing_failure(analytics_consumer):
    message = MagicMock(value=b'{"metric": "rides"}')  # Malformed message
    with patch.object(analytics_consumer, "consume", return_value=[message]):
        with pytest.raises(KeyError):
            await analytics_consumer.consume("analytics_topic")


@pytest.mark.asyncio
async def test_consumer_cleanup(analytics_consumer):
    with patch.object(analytics_consumer, "cleanup", return_value=True) as mock_cleanup:
        await analytics_consumer.cleanup()
        mock_cleanup.assert_called_once()
