from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Booking, Driver, User
from db.database import get_db
from app.schemas.analytics import AnalyticsResponse

router = APIRouter()

@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)

    last_24_hours = now - timedelta(hours=24)

    # Total number of bookings in the last 24 hours
    total_bookings = (
        db.query(func.count(Booking.id)).filter(Booking.date >= last_24_hours).scalar()
    )

    # Total revenue in the last 24 hours
    total_revenue = (
        db.query(func.sum(Booking.price)).filter(Booking.date >= last_24_hours).scalar()
    )

    # Average price per booking
    avg_price = (
        db.query(func.avg(Booking.price)).filter(Booking.date >= last_24_hours).scalar()
    )

    # Most popular pickup locations
    popular_pickups = (
        db.query(Booking.pickup_location, func.count(Booking.id).label("count"))
        .filter(Booking.date >= last_24_hours)
        .group_by(Booking.pickup_location)
        .order_by(func.count(Booking.id).desc())
        .limit(5)
        .all()
    )

    # Number of active drivers
    active_drivers = (
        db.query(func.count(Driver.id)).filter(Driver.is_available == True).scalar()
    )

    # Number of new users registered in the last 24 hours
    new_users = (
        db.query(func.count(User.id)).filter(User.created_at >= last_24_hours).scalar()
    )

    return {
        "total_bookings": total_bookings,
        "total_revenue": float(total_revenue) if total_revenue else 0,
        "average_price": float(avg_price) if avg_price else 0,
        "popular_pickup_locations": [
            {"location": loc, "count": count} for loc, count in popular_pickups
        ],
        "active_drivers": active_drivers,
        "new_users": new_users,
    }