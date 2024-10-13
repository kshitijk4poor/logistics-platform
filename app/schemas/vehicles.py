from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class VehicleTypeEnum(str, Enum):
    sedan = "sedan"
    suv = "suv"
    van = "van"
    truck = "truck"


class VehicleSchema(BaseModel):
    vehicle_type: VehicleTypeEnum = Field(..., description="Type of the vehicle")
    make: str = Field(..., description="Make of the vehicle")
    model: str = Field(..., description="Model of the vehicle")
    year: int = Field(..., description="Year of manufacture")
    license_plate: str = Field(..., description="License plate number")
    capacity: int = Field(..., description="Passenger capacity")
    status: str = Field(
        default="available", description="Current status of the vehicle"
    )


class VehicleResponse(VehicleSchema):
    id: int = Field(..., description="Unique identifier for the vehicle")
    driver_id: Optional[int] = Field(
        None, description="ID of the assigned driver, if any"
    )

    class Config:
        orm_mode = True
