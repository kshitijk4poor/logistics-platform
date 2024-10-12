import math
from datetime import datetime
from typing import Optional

import aioredis
import h3  # Added H3 for spatial indexing

from app.schemas.pricing import PricingSchema
from scripts.caching import cache

# Configuration for pricing factors
BASE_FARE = {"economy": 5.0, "standard": 7.0, "premium": 10.0}
COST_PER_KM = {"economy": 1.5, "standard": 2.0, "premium": 2.5}
SURGE_MULTIPLIER = 1.0  # This can be dynamically fetched from a configuration or real-time metrics
TIME_OF_DAY_MULTIPLIER = 1.0  # Adjust based on peak hours
MIN_PRICE = 10.0
MAX_PRICE = 500.0

# H3 configuration
H3_RESOLUTION = 9

def get_h3_index(lat: float, lon: float) -> str:
    """
    Convert latitude and longitude to H3 index.
    """
    return h3.geo_to_h3(lat, lon, H3_RESOLUTION)

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points
    on the Earth specified in decimal degrees.
    """
    R = 6371  # Radius of Earth in kilometers
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c  # Distance in kilometers

def get_surge_multiplier(pickup_h3: str) -> float:
    """
    Determine surge multiplier based on the H3 index of the pickup location.
    This is a placeholder; implement actual logic as per requirements.
    """
    # Example logic: Fetch surge multiplier from a cached or database value based on H3 index
    # surge_data = fetch_surge_data(pickup_h3)
    # return surge_data.get('multiplier', 1.0)
    return SURGE_MULTIPLIER

def get_time_of_day_multiplier(pickup_time: datetime) -> float:
    """
    Determine time of day multiplier based on pickup time.
    """
    hour = pickup_time.hour
    if 7 <= hour <= 9 or 17 <= hour <= 19:
        # Peak hours
        return 1.2
    elif 22 <= hour or hour <= 5:
        # Night hours
        return 1.3
    else:
        return 1.0

async def calculate_price(pricing_data: PricingSchema) -> float:
    """
    Calculate the price of a ride based on various factors including distance,
    surge pricing, and time of day. Utilizes H3 for efficient spatial computations.
    """
    # Generate H3 indices for pickup and dropoff locations
    pickup_h3 = get_h3_index(
        pricing_data.pickup_latitude, pricing_data.pickup_longitude
    )
    dropoff_h3 = get_h3_index(
        pricing_data.dropoff_latitude, pricing_data.dropoff_longitude
    )

    # Create a unique cache key based on H3 indices and other pricing parameters
    cache_key = f"price:{pricing_data.vehicle_type}:{pickup_h3}:{dropoff_h3}:{pricing_data.scheduled_time or 'now'}"
    cached_price = await cache.get(cache_key)
    if cached_price:
        return float(cached_price)

    # Calculate distance using Haversine formula
    distance_km = haversine(
        pricing_data.pickup_latitude,
        pricing_data.pickup_longitude,
        pricing_data.dropoff_latitude,
        pricing_data.dropoff_longitude,
    )

    # Handle zero distance
    if distance_km == 0:
        raise ValueError("Pickup and dropoff locations cannot be the same.")

    # Calculate base price
    base_fare = BASE_FARE.get(pricing_data.vehicle_type, 5.0)
    distance_cost = COST_PER_KM.get(pricing_data.vehicle_type, 1.5) * distance_km

    # Total before multipliers
    total = base_fare + distance_cost

    # Apply surge multiplier based on pickup location's H3 index
    surge = get_surge_multiplier(pickup_h3)
    total *= surge

    # Apply time of day multiplier
    if pricing_data.scheduled_time:
        pickup_time = datetime.fromisoformat(pricing_data.scheduled_time)
    else:
        pickup_time = datetime.utcnow()
    time_multiplier = get_time_of_day_multiplier(pickup_time)
    total *= time_multiplier

    # Apply minimum and maximum price constraints
    total = max(total, MIN_PRICE)
    total = min(total, MAX_PRICE)

    # Round to two decimal places
    total = round(total, 2)

    # Cache the calculated price for future use
    await cache.set(cache_key, total, expire=300)  # Cache for 5 minutes

    return total