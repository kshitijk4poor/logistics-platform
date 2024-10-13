from enum import Enum

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class VehicleTypeEnum(str, Enum):
    economy = "economy"
    standard = "standard"
    premium = "premium"


class BookingStatusEnum(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    phone_number = Column(String, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    payment_info = Column(
        String, nullable=True
    )  # Assuming payment info is stored as a string
    bookings = relationship(
        "Booking", back_populates="user", cascade="all, delete-orphan"
    )


class Driver(Base):
    __tablename__ = "drivers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    phone_number = Column(String, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    vehicle_type = Column(SqlEnum(VehicleTypeEnum), nullable=False, index=True)
    car_info = Column(String, nullable=True)
    location = Column(Geometry("POINT"), nullable=True)
    is_available = Column(Boolean, default=True)


class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    driver_id = Column(Integer, ForeignKey("drivers.id"))
    pickup_location = Column(Geometry("POINT"))
    dropoff_location = Column(Geometry("POINT"))
    vehicle_type = Column(SqlEnum(VehicleTypeEnum))
    price = Column(Float)
    date = Column(DateTime, nullable=False)
    status = Column(SqlEnum(BookingStatusEnum), nullable=False)
    user = relationship("User", back_populates="bookings")
    driver = relationship("Driver")
