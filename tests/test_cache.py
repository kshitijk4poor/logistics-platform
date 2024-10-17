import pytest
from unittest.mock import patch, MagicMock
from app.services.caching import CachingService

@pytest.fixture
def caching_service():
    return CachingService()

@pytest.mark.asyncio
async def test_cache_driver_availability(caching_service):
    driver_id = "driver_123"
    availability_data = {"available": True}
    with patch.object(caching_service, 'set', return_value=True) as mock_set:
        result = await caching_service.cache_driver_availability(driver_id, availability_data)
        assert result is True
        mock_set.assert_called_once_with(f"driver_availability:{driver_id}", availability_data)

@pytest.mark.asyncio
async def test_retrieve_cached_driver_availability(caching_service):
    driver_id = "driver_123"
    availability_data = {"available": True}
    with patch.object(caching_service, 'get', return_value=availability_data) as mock_get:
        result = await caching_service.get_driver_availability(driver_id)
        assert result == availability_data
        mock_get.assert_called_once_with(f"driver_availability:{driver_id}")

@pytest.mark.asyncio
async def test_cache_expiration_handling(caching_service):
    driver_id = "driver_123"
    with patch.object(caching_service, 'get', return_value=None) as mock_get:
        result = await caching_service.get_driver_availability(driver_id)
        assert result is None
        mock_get.assert_called_once_with(f"driver_availability:{driver_id}")

@pytest.mark.asyncio
async def test_cache_booking_status(caching_service):
    booking_id = "booking_123"
    status_data = {"status": "confirmed"}
    with patch.object(caching_service, 'set', return_value=True) as mock_set:
        result = await caching_service.cache_booking_status(booking_id, status_data)
        assert result is True
        mock_set.assert_called_once_with(f"booking_status:{booking_id}", status_data)

@pytest.mark.asyncio
async def test_retrieve_cached_booking_status(caching_service):
    booking_id = "booking_123"
    status_data = {"status": "confirmed"}
    with patch.object(caching_service, 'get', return_value=status_data) as mock_get:
        result = await caching_service.get_booking_status(booking_id)
        assert result == status_data
        mock_get.assert_called_once_with(f"booking_status:{booking_id}")

@pytest.mark.asyncio
async def test_retrieve_non_existent_driver_availability(caching_service):
    driver_id = "non_existent_driver"
    with patch.object(caching_service, 'get', return_value=None) as mock_get:
        result = await caching_service.get_driver_availability(driver_id)
        assert result is None
        mock_get.assert_called_once_with(f"driver_availability:{driver_id}")

@pytest.mark.asyncio
async def test_redis_connection_failure(caching_service):
    driver_id = "driver_123"
    with patch.object(caching_service, 'get', side_effect=Exception("Redis connection error")):
        with pytest.raises(Exception):
            await caching_service.get_driver_availability(driver_id)