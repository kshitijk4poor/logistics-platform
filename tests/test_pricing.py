import pytest
from datetime import datetime

from app.services.pricing import calculate_price
from app.schemas.pricing import PricingSchema

@pytest.mark.asyncio
async def test_calculate_price_off_peak():
    pricing_data = {
        "pickup_latitude": 37.7749,
        "pickup_longitude": -122.4194,
        "dropoff_latitude": 37.8044,
        "dropoff_longitude": -122.2711,
        "vehicle_type": "standard",
        "scheduled_time": "2023-10-10T14:30:00Z"
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
        "scheduled_time": "2023-10-10T18:30:00Z"
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
        "scheduled_time": "2023-10-10T09:30:00Z"
    }
    price = await calculate_price(pricing_data)
    assert price >= 10.0
    assert price <= 500.0