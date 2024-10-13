import json
import logging
from datetime import datetime, timedelta

import aioredis
from celery import Celery
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, Driver, User
from db.database import SessionLocal, engine

# Setup basic configuration for logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

app = Celery("tasks", broker="redis://localhost:6379/0")


async def get_redis_client():
    return await aioredis.from_url("redis://localhost", decode_responses=True)


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(3600.0, compute_analytics.s(), name="compute every hour")


@app.task
async def compute_analytics():
    async with AsyncSession(engine) as db:
        try:
            logging.info("Starting computation of analytics")
            now = datetime.now()
            last_24_hours = now - timedelta(hours=24)

            hourly_data = []
            for hour in range(24):
                start_time = last_24_hours + timedelta(hours=hour)
                end_time = start_time + timedelta(hours=1)

                result = await db.execute(
                    select(
                        func.count(Booking.id).label("bookings_count"),
                        func.sum(Booking.price).label("revenue"),
                    ).where(Booking.date.between(start_time, end_time))
                )
                row = result.first()
                hourly_data.append(
                    {
                        "hour": start_time.strftime("%Y-%m-%d %H:00"),
                        "bookings": row.bookings_count or 0,
                        "revenue": float(row.revenue) if row.revenue else 0,
                    }
                )

            total_bookings = await db.scalar(
                select(func.count(Booking.id)).where(Booking.date >= last_24_hours)
            )
            total_revenue = await db.scalar(
                select(func.sum(Booking.price)).where(Booking.date >= last_24_hours)
            )
            avg_price = await db.scalar(
                select(func.avg(Booking.price)).where(Booking.date >= last_24_hours)
            )
            active_drivers = await db.scalar(
                select(func.count(Driver.id)).where(Driver.is_available == True)
            )
            new_users = await db.scalar(
                select(func.count(User.id)).where(User.created_at >= last_24_hours)
            )

            # Compute popular pickup locations
            popular_locations_result = await db.execute(
                select(Booking.pickup_location, func.count(Booking.id).label("count"))
                .where(Booking.date >= last_24_hours)
                .group_by(Booking.pickup_location)
                .order_by(desc("count"))
                .limit(5)
            )
            popular_pickup_locations = [
                {"pickup_location": row.pickup_location, "count": row.count}
                for row in popular_locations_result
            ]

            analytics_data = {
                "timestamp": now.isoformat(),
                "total_bookings": total_bookings or 0,
                "total_revenue": float(total_revenue) if total_revenue else 0,
                "average_price": float(avg_price) if avg_price else 0,
                "active_drivers": active_drivers or 0,
                "new_users": new_users or 0,
                "hourly_data": hourly_data,
                "popular_pickup_locations": popular_pickup_locations,
            }

            redis = await get_redis_client()
            await redis.set(REDIS_KEY, json.dumps(analytics_data))
            await redis.close()

            logging.info("Analytics computed and stored successfully")
            return "Analytics computed and stored successfully"

        except Exception as e:
            logging.error(f"Error in compute_analytics: {e}")
            raise
