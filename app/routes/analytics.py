from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, Driver, User
from app.schemas.analytics import AnalyticsResponse, PopularPickupLocation
from db.database import get_db

router = APIRouter()


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    last_24_hours = now - timedelta(hours=24)

    # Total number of bookings in the last 24 hours
    total_bookings = await db.scalar(
        select(func.count(Booking.id)).where(Booking.date >= last_24_hours)
    )

    # Total revenue in the last 24 hours
    total_revenue = await db.scalar(
        select(func.sum(Booking.price)).where(Booking.date >= last_24_hours)
    )

    # Average price per booking
    avg_price = await db.scalar(
        select(func.avg(Booking.price)).where(Booking.date >= last_24_hours)
    )

    # Most popular pickup locations
    popular_pickups_query = (
        select(Booking.pickup_location, func.count(Booking.id).label("count"))
        .where(Booking.date >= last_24_hours)
        .group_by(Booking.pickup_location)
        .order_by(func.count(Booking.id).desc())
        .limit(5)
    )
    result = await db.execute(popular_pickups_query)
    popular_pickups = result.all()

    # Number of active drivers
    active_drivers = await db.scalar(
        select(func.count(Driver.id)).where(Driver.is_available == True)
    )

    # Number of new users registered in the last 24 hours
    new_users = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= last_24_hours)
    )

    # Transform popular pickups into response format
    popular_pickup_locations = [
        PopularPickupLocation(location=loc, count=count)
        for loc, count in popular_pickups
    ]

    return AnalyticsResponse(
        total_bookings=total_bookings,
        total_revenue=float(total_revenue) if total_revenue else 0.0,
        average_price=float(avg_price) if avg_price else 0.0,
        popular_pickup_locations=popular_pickup_locations,
        active_drivers=active_drivers,
        new_users=new_users,
    )
