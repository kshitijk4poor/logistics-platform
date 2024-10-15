from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class BookingStatus(str, Enum):
    pending = "pending"
    scheduled = "scheduled"
    confirmed = "confirmed"
    en_route = "en_route"
    goods_collected = "goods_collected"
    delivered = "delivered"
    cancelled = "cancelled"
    completed = "completed"


class StatusUpdate(BaseModel):
    status: BookingStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)


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
    status_history: List[StatusUpdate] = Field(
        default_factory=list, description="History of status updates."
    )


class BookingRequest(BaseModel):
    user_id: int
    pickup_latitude: float
    pickup_longitude: float
    dropoff_latitude: float
    dropoff_longitude: float
    vehicle_type: str
    scheduled_time: Optional[datetime] = None
