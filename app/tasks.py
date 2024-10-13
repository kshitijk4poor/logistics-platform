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


@app.task(bind=True, max_retries=3, default_retry_delay=60)
async def compute_analytics(self):
    async with AsyncSession(engine) as db:
        try:
            redis = await get_redis_client()
            
            # Fetch incrementally updated data
            total_bookings = int(await redis.get("analytics:total_bookings") or 0)
            total_revenue = float(await redis.get("analytics:total_revenue") or 0)
            
            # Calculate average price from recent prices
            recent_prices = await redis.lrange("analytics:recent_prices", 0, -1)
            avg_price = sum(map(float, recent_prices)) / len(recent_prices) if recent_prices else 0
            
            active_drivers = int(await redis.get("analytics:active_drivers") or 0)
            
            # Fetch other data that needs full recomputation
            last_24_hours = datetime.now() - timedelta(hours=24)

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

            # Store the final computed analytics
            analytics_data = {
                "timestamp": datetime.now().isoformat(),
                "total_bookings": total_bookings,
                "total_revenue": total_revenue,
                "average_price": avg_price,
                "active_drivers": active_drivers,
                "new_users": new_users or 0,
                "hourly_data": hourly_data,
                "popular_pickup_locations": popular_pickup_locations,
            }
            await redis.set(REDIS_KEY, json.dumps(analytics_data))

            logging.info("Analytics computed and stored successfully")
            return "Analytics computed and stored successfully"

        except Exception as e:
            logging.error(f"Error in compute_analytics: {e}")
            self.retry(exc=e)
