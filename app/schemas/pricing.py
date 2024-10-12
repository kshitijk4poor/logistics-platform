from typing import Optional

from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum

class VehicleType(str, Enum):
    economy = "economy"
    standard = "standard"
    premium = "premium"

class PricingSchema(BaseModel):
    pickup_latitude: float = Field(
        ..., ge=-90.0, le=90.0, description="Latitude of the pickup location."
    )
    pickup_longitude: float = Field(
        ..., ge=-180.0, le=180.0, description="Longitude of the pickup location."
    )
    dropoff_latitude: float = Field(
        ..., ge=-90.0, le=90.0, description="Latitude of the dropoff location."
    )
    dropoff_longitude: float = Field(
        ..., ge=-180.0, le=180.0, description="Longitude of the dropoff location."
    )
    vehicle_type: VehicleType = Field(
        ..., description="Type of vehicle selected for the booking."
    )
    scheduled_time: Optional[datetime] = Field(
        None, description="Scheduled time for the booking in ISO format."
    )

    @validator("scheduled_time")
    def validate_scheduled_time(cls, v):
        return v  # Pydantic automatically validates datetime fields