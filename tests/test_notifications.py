import pytest
from unittest.mock import patch, MagicMock
from app.services.communication.notification import NotificationService

@pytest.fixture
def notification_service():
    return NotificationService()

@pytest.mark.asyncio
async def test_notify_driver_assignment_success(notification_service):
    driver_id = "driver_123"
    booking_id = "booking_123"
    with patch.object(notification_service, 'send_notification', return_value=True) as mock_send:
        result = await notification_service.notify_driver_assignment(driver_id, booking_id)
        assert result is True
        mock_send.assert_called_once_with(driver_id, f"New booking assigned: {booking_id}")

@pytest.mark.asyncio
async def test_notify_driver_assignment_failure(notification_service):
    driver_id = "driver_123"
    booking_id = "booking_123"
    with patch.object(notification_service, 'send_notification', side_effect=Exception("Notification failure")):
        with pytest.raises(Exception):
            await notification_service.notify_driver_assignment(driver_id, booking_id)

@pytest.mark.asyncio
async def test_notify_nearby_drivers_success(notification_service):
    driver_ids = ["driver_1", "driver_2", "driver_3"]
    booking_id = "booking_123"
    with patch.object(notification_service, 'send_notification', return_value=True) as mock_send:
        results = await notification_service.notify_nearby_drivers(driver_ids, booking_id)
        assert all(results)
        assert mock_send.call_count == len(driver_ids)

@pytest.mark.asyncio
async def test_notify_nearby_drivers_partial_failure(notification_service):
    driver_ids = ["driver_1", "driver_2", "driver_3"]
    booking_id = "booking_123"
    with patch.object(notification_service, 'send_notification', side_effect=[True, Exception("Notification failure"), True]):
        results = await notification_service.notify_nearby_drivers(driver_ids, booking_id)
        assert results == [True, False, True]

@pytest.mark.asyncio
async def test_message_formatting(notification_service):
    driver_id = "driver_123"
    booking_id = "booking_123"
    message = notification_service.format_message(driver_id, booking_id)
    assert "driver_123" in message
    assert "booking_123" in message

@pytest.mark.asyncio
async def test_handle_malformed_notification_data(notification_service):
    driver_id = None
    booking_id = "booking_123"
    with pytest.raises(ValueError):
        notification_service.format_message(driver_id, booking_id)

@pytest.mark.asyncio
async def test_notify_connected_and_disconnected_drivers(notification_service):
    driver_ids = ["connected_driver", "disconnected_driver"]
    booking_id = "booking_123"
    with patch.object(notification_service, 'send_notification', side_effect=[True, False]):
        results = await notification_service.notify_nearby_drivers(driver_ids, booking_id)
        assert results == [True, False]

@pytest.mark.asyncio
async def test_prevent_duplicate_notifications(notification_service):
    driver_id = "driver_123"
    booking_id = "booking_123"
    with patch.object(notification_service, 'send_notification', return_value=True) as mock_send:
        await notification_service.notify_driver_assignment(driver_id, booking_id)
        await notification_service.notify_driver_assignment(driver_id, booking_id)
        assert mock_send.call_count == 1  # Assuming the service prevents duplicates