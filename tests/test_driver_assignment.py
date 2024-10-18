import asyncio
from unittest.mock import MagicMock, patch

import pytest
from app.services.assignment import (assign_driver_to_booking,
                                     find_nearest_driver)


@pytest.mark.asyncio
async def test_find_nearest_driver_success():
    location = {"latitude": 37.7749, "longitude": -122.4194}
    with patch(
        "app.services.assignment.get_available_drivers",
        return_value=[{"driver_id": "1", "distance": 5}],
    ):
        driver = await find_nearest_driver(location)
        assert driver["driver_id"] == "1"


@pytest.mark.asyncio
async def test_find_nearest_driver_no_available():
    location = {"latitude": 37.7749, "longitude": -122.4194}
    with patch("app.services.assignment.get_available_drivers", return_value=[]):
        driver = await find_nearest_driver(location)
        assert driver is None


@pytest.mark.asyncio
async def test_find_nearest_driver_with_radius_expansion():
    location = {"latitude": 37.7749, "longitude": -122.4194}
    with patch(
        "app.services.assignment.get_available_drivers",
        side_effect=[[], [{"driver_id": "2", "distance": 10}]],
    ):
        driver = await find_nearest_driver(location)
        assert driver["driver_id"] == "2"


@pytest.mark.asyncio
async def test_assign_driver_to_booking_success():
    booking_id = "booking_123"
    driver_id = "driver_123"
    with patch("app.services.assignment.is_driver_available", return_value=True), patch(
        "app.services.assignment.update_booking_with_driver", return_value=True
    ):
        result = await assign_driver_to_booking(booking_id, driver_id)
        assert result is True


@pytest.mark.asyncio
async def test_assign_driver_to_non_existent_booking():
    booking_id = "non_existent_booking"
    driver_id = "driver_123"
    with patch("app.services.assignment.is_driver_available", return_value=True), patch(
        "app.services.assignment.update_booking_with_driver",
        side_effect=Exception("Booking not found"),
    ):
        with pytest.raises(Exception):
            await assign_driver_to_booking(booking_id, driver_id)


@pytest.mark.asyncio
async def test_prevent_multiple_assignments():
    booking_id = "booking_123"
    driver_id = "driver_123"
    with patch("app.services.assignment.is_driver_available", return_value=False):
        with pytest.raises(Exception):
            await assign_driver_to_booking(booking_id, driver_id)


@pytest.mark.asyncio
async def test_handle_invalid_booking_data():
    booking_data = {"invalid_key": "value"}
    with pytest.raises(KeyError):
        await find_nearest_driver(booking_data)


@pytest.mark.asyncio
async def test_thread_safety_in_concurrent_assignments():
    booking_id = "booking_123"
    driver_id = "driver_123"
    with patch("app.services.assignment.is_driver_available", return_value=True), patch(
        "app.services.assignment.update_booking_with_driver", return_value=True
    ):
        # Simulate concurrent assignments
        results = await asyncio.gather(
            assign_driver_to_booking(booking_id, driver_id),
            assign_driver_to_booking(booking_id, driver_id),
            return_exceptions=True,
        )
        assert any(isinstance(result, Exception) for result in results)
