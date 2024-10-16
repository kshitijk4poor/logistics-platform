from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.booking import BookingStatus


class BookingAssignment(BaseModel):
    booking_id: int
    pickup_location: str
    dropoff_location: str
    vehicle_type: str
    price: float
    scheduled_time: Optional[datetime] = None


class StatusUpdateRequest(BaseModel):
    status: BookingStatus


class AcceptBookingResponse(BaseModel):
    booking_id: int
    pickup_location: str
    dropoff_location: str
    vehicle_type: str
    price: float
    scheduled_time: Optional[datetime] = None
    status: BookingStatus
