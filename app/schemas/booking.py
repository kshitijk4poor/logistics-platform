from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class BookingStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class BookingResponse(BaseModel):
    booking_id: int = Field(..., description="Unique identifier for the booking.")
    user_id: int = Field(..., description="ID of the user who made the booking.")
    driver_id: Optional[int] = Field(
        None, description="ID of the assigned driver, if any."
    )
    pickup_location: str = Field(
        ..., description="Pickup location in 'POINT(longitude latitude)' format."
    )
    dropoff_location: str = Field(
        ..., description="Dropoff location in 'POINT(longitude latitude)' format."
    )
    vehicle_type: str = Field(..., description="Type of vehicle for the booking.")
    price: float = Field(..., description="Calculated price for the booking.")
    date: datetime = Field(..., description="Date and time of the booking.")
    status: BookingStatus = Field(..., description="Current status of the booking.")


class BookingRequest(BaseModel):
    user_id: int
    pickup_latitude: float
    pickup_longitude: float
    dropoff_latitude: float
    dropoff_longitude: float
    vehicle_type: str
    scheduled_time: Optional[datetime] = None
