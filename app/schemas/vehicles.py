from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class VehicleTypeEnum(str, Enum):
    refrigerated_truck = "refrigerated_truck"
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


class VehicleUpdate(BaseModel):
    vehicle_type: Optional[VehicleTypeEnum] = Field(
        None, description="Type of the vehicle"
    )
    make: Optional[str] = Field(None, description="Make of the vehicle")
    model: Optional[str] = Field(None, description="Model of the vehicle")
    year: Optional[int] = Field(None, description="Year of manufacture")
    license_plate: Optional[str] = Field(None, description="License plate number")
    capacity: Optional[int] = Field(None, description="Passenger capacity")
    status: Optional[str] = Field(None, description="Current status of the vehicle")


class VehicleResponse(VehicleSchema):
    id: int = Field(..., description="Unique identifier for the vehicle")
    driver_id: Optional[int] = Field(
        None, description="ID of the assigned driver, if any"
    )
