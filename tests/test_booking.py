import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime
from app.services.booking import create_booking, assign_driver
from app.tasks import process_scheduled_booking
from app.models import Booking, Driver

@pytest.mark.asyncio
async def test_create_new_booking():
    booking_data = {
        "pickup_latitude": 37.7749,
        "pickup_longitude": -122.4194,
        "dropoff_latitude": 37.8044,
        "dropoff_longitude": -122.2711,
        "vehicle_type": "standard",
        "scheduled_time": "2023-10-10T14:30:00Z",
    }
    booking = await create_booking(booking_data)
    assert booking is not None
    assert booking.status == "pending"

@pytest.mark.asyncio
async def test_create_scheduled_booking():
    booking_data = {
        "pickup_latitude": 37.7749,
        "pickup_longitude": -122.4194,
        "dropoff_latitude": 37.8044,
        "dropoff_longitude": -122.2711,
        "vehicle_type": "standard",
        "scheduled_time": "2023-12-10T14:30:00Z",
    }
    booking = await create_booking(booking_data)
    assert booking.scheduled_time > datetime.now()

@pytest.mark.asyncio
async def test_create_immediate_booking():
    booking_data = {
        "pickup_latitude": 37.7749,
        "pickup_longitude": -122.4194,
        "dropoff_latitude": 37.8044,
        "dropoff_longitude": -122.2711,
        "vehicle_type": "standard",
        "scheduled_time": datetime.now().isoformat(),
    }
    booking = await create_booking(booking_data)
    assert booking.scheduled_time <= datetime.now()

@pytest.mark.asyncio
async def test_booking_vehicle_under_maintenance():
    booking_data = {
        "pickup_latitude": 37.7749,
        "pickup_longitude": -122.4194,
        "dropoff_latitude": 37.8044,
        "dropoff_longitude": -122.2711,
        "vehicle_type": "maintenance",
        "scheduled_time": "2023-10-10T14:30:00Z",
    }
    with pytest.raises(ValueError):
        await create_booking(booking_data)

@pytest.mark.asyncio
async def test_booking_overlapping():
    booking_data = {
        "pickup_latitude": 37.7749,
        "pickup_longitude": -122.4194,
        "dropoff_latitude": 37.8044,
        "dropoff_longitude": -122.2711,
        "vehicle_type": "standard",
        "scheduled_time": "2023-10-10T14:30:00Z",
    }
    await create_booking(booking_data)
    with pytest.raises(ValueError):
        await create_booking(booking_data)

@pytest.mark.asyncio
async def test_driver_assignment():
    booking = Booking(status="pending")
    driver = Driver(available=True)
    with patch('app.services.booking.find_available_driver', return_value=driver):
        await assign_driver(booking)
        assert booking.status == "confirmed"

@pytest.mark.asyncio
async def test_no_available_driver():
    booking = Booking(status="pending")
    with patch('app.services.booking.find_available_driver', return_value=None):
        with pytest.raises(Exception):
            await assign_driver(booking)

@pytest.mark.asyncio
async def test_status_update_to_cancelled():
    booking = Booking(status="pending")
    booking.status = "cancelled"
    assert booking.status == "cancelled"

@pytest.mark.asyncio
async def test_database_failure_during_booking():
    booking_data = {
        "pickup_latitude": 37.7749,
        "pickup_longitude": -122.4194,
        "dropoff_latitude": 37.8044,
        "dropoff_longitude": -122.2711,
        "vehicle_type": "standard",
        "scheduled_time": "2023-10-10T14:30:00Z",
    }
    with patch('app.services.booking.create_booking', side_effect=Exception("Database error")):
        with pytest.raises(Exception):
            await create_booking(booking_data)

@pytest.mark.asyncio
async def test_exception_handling_in_background_tasks():
    with patch('app.tasks.process_scheduled_booking', side_effect=Exception("Task error")):
        with pytest.raises(Exception):
            await process_scheduled_booking()