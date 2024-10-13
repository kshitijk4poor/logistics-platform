import math
from datetime import datetime
from typing import Optional

import h3

from app.dependencies import cache
from app.schemas.pricing import PricingSchema

# Configuration for pricing factors
BASE_FARE = {"economy": 5.0, "standard": 7.0, "premium": 10.0}
COST_PER_KM = {"economy": 1.5, "standard": 2.0, "premium": 2.5}
SURGE_MULTIPLIER = (
    1.0  # This can be dynamically fetched from configuration or real-time metrics
)
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
    Calculate the great-circle distance between two points on the Earth specified in decimal degrees.
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
    # Example logic: Increase surge in high-demand areas
    high_demand_zones = {"8928308280fffff", "8928308283fffff"}  # Example H3 indices
    if pickup_h3 in high_demand_zones:
        return 1.5  # 50% surge
    return SURGE_MULTIPLIER


def get_time_of_day_multiplier(pickup_time: datetime) -> float:
    """
    Determine time of day multiplier based on pickup time.
    """
    hour = pickup_time.hour
    if 7 <= hour <= 9 or 17 <= hour <= 19:
        return 1.5  # Peak hours
    return 1.0  # Off-peak hours


def calculate_h3_distance(pickup_h3: str, dropoff_h3: str) -> float:
    """
    Calculate the approximate distance between two H3 indices.
    """
    # Use the H3 distance function to get the number of hexagons between two indices
    hex_distance = h3.h3_distance(pickup_h3, dropoff_h3)
    # Convert hex distance to kilometers (approximate conversion factor)
    return hex_distance * 0.15  # Assuming each hexagon is ~150m


async def calculate_price(pricing_data: dict) -> float:
    """
    Calculate the price based on booking data.
    """
    pricing_schema = PricingSchema(**pricing_data)

    pickup_lat = pricing_schema.pickup_latitude
    pickup_lng = pricing_schema.pickup_longitude
    dropoff_lat = pricing_schema.dropoff_latitude
    dropoff_lng = pricing_schema.dropoff_longitude
    vehicle_type = pricing_schema.vehicle_type
    scheduled_time = pricing_schema.scheduled_time

    # Calculate distance using H3
    pickup_h3 = get_h3_index(pickup_lat, pickup_lng)
    dropoff_h3 = get_h3_index(dropoff_lat, dropoff_lng)
    distance = calculate_h3_distance(pickup_h3, dropoff_h3)

    # Base fare and cost per km
    base_fare = BASE_FARE.get(vehicle_type, BASE_FARE["standard"])
    cost_per_km = COST_PER_KM.get(vehicle_type, COST_PER_KM["standard"])

    total = base_fare + (cost_per_km * distance)

    # Apply surge multiplier based on pickup location's H3 index
    surge = get_surge_multiplier(pickup_h3)
    total *= surge

    # Apply time of day multiplier
    if scheduled_time:
        pickup_time = datetime.fromisoformat(scheduled_time)
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
    cache_key = (
        f"price:{pickup_lat},{pickup_lng}:{dropoff_lat},{dropoff_lng}:{vehicle_type}"
    )
    await cache.set(cache_key, total, expire=300)  # Cache for 5 minutes

    return total
