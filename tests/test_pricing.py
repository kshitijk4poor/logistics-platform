from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from app.schemas.pricing import PricingSchema
from app.services.pricing import calculate_price


@pytest.mark.asyncio
async def test_calculate_price_off_peak():
    pricing_data = {
        "pickup_latitude": 37.7749,
        "pickup_longitude": -122.4194,
        "dropoff_latitude": 37.8044,
        "dropoff_longitude": -122.2711,
        "vehicle_type": "standard",
        "scheduled_time": "2023-10-10T14:30:00Z",
    }
    price = await calculate_price(pricing_data)
    assert price >= 10.0
    assert price <= 500.0


@pytest.mark.asyncio
async def test_calculate_price_peak():
    pricing_data = {
        "pickup_latitude": 37.7749,
        "pickup_longitude": -122.4194,
        "dropoff_latitude": 37.8044,
        "dropoff_longitude": -122.2711,
        "vehicle_type": "premium",
        "scheduled_time": "2023-10-10T18:30:00Z",
    }
    price = await calculate_price(pricing_data)
    assert price >= 10.0
    assert price <= 500.0


@pytest.mark.asyncio
async def test_calculate_price_high_demand():
    pricing_data = {
        "pickup_latitude": 37.7749,
        "pickup_longitude": -122.4194,
        "dropoff_latitude": 37.8044,
        "dropoff_longitude": -122.2711,
        "vehicle_type": "economy",
        "scheduled_time": "2023-10-10T09:30:00Z",
    }
    price = await calculate_price(pricing_data)
    assert price >= 10.0
    assert price <= 500.0


@pytest.mark.asyncio
async def test_calculate_price_valid_data_peak_hours():
    pricing_data = {
        "pickup_latitude": 37.7749,
        "pickup_longitude": -122.4194,
        "dropoff_latitude": 37.8044,
        "dropoff_longitude": -122.2711,
        "vehicle_type": "standard",
        "scheduled_time": "2023-10-10T18:30:00Z",
    }

    with patch(
        "app.services.pricing.pricing_service.get_distance_duration"
    ) as mock_get_distance:
        mock_get_distance.return_value = {"distance_km": 10, "duration_min": 15}
        with patch(
            "app.services.pricing.pricing_service.get_surge_multiplier",
            AsyncMock(return_value=1.5),
        ):
            price = await calculate_price(pricing_data)
            assert (15.0 + 3.0 * 10) * 1.5 <= price <= 10000.0


@pytest.mark.asyncio
async def test_calculate_price_invalid_vehicle_type():
    pricing_data = {
        "pickup_latitude": 37.7749,
        "pickup_longitude": -122.4194,
        "dropoff_latitude": 37.8044,
        "dropoff_longitude": -122.2711,
        "vehicle_type": "invalid_type",
        "scheduled_time": "2023-10-10T14:30:00Z",
    }

    with pytest.raises(ValueError) as exc_info:
        await calculate_price(pricing_data)
    assert "Invalid vehicle type provided." in str(exc_info.value)


@pytest.mark.asyncio
async def test_calculate_price_zero_distance():
    pricing_data = {
        "pickup_latitude": 37.7749,
        "pickup_longitude": -122.4194,
        "dropoff_latitude": 37.7749,
        "dropoff_longitude": -122.4194,
        "vehicle_type": "standard",
        "scheduled_time": "2023-10-10T14:30:00Z",
    }
    price = await calculate_price(pricing_data)
    assert price >= 10.0


@pytest.mark.asyncio
async def test_calculate_price_extremely_long_distance():
    pricing_data = {
        "pickup_latitude": 37.7749,
        "pickup_longitude": -122.4194,
        "dropoff_latitude": 40.7128,
        "dropoff_longitude": -74.0060,
        "vehicle_type": "standard",
        "scheduled_time": "2023-10-10T14:30:00Z",
    }
    price = await calculate_price(pricing_data)
    assert price <= 10000.0


@pytest.mark.asyncio
async def test_calculate_price_missing_pickup_coordinates():
    pricing_data = {
        "dropoff_latitude": 37.8044,
        "dropoff_longitude": -122.2711,
        "vehicle_type": "standard",
        "scheduled_time": "2023-10-10T14:30:00Z",
    }
    with pytest.raises(KeyError):
        await calculate_price(pricing_data)


@pytest.mark.asyncio
async def test_calculate_price_invalid_latitude_type():
    pricing_data = {
        "pickup_latitude": "invalid_latitude",
        "pickup_longitude": -122.4194,
        "dropoff_latitude": 37.8044,
        "dropoff_longitude": -122.2711,
        "vehicle_type": "standard",
        "scheduled_time": "2023-10-10T14:30:00Z",
    }
    with pytest.raises(TypeError):
        await calculate_price(pricing_data)
