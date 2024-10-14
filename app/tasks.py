import json
import logging
from datetime import datetime, timedelta

import aioredis
from celery import Celery
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, BookingStatusEnum, Driver, User
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
            total_revenue = float(await redis.get("analytics:total_revenue") or 0.0)
            recent_prices = json.loads(
                await redis.get("analytics:recent_prices") or "[]"
            )
            active_drivers = int(await redis.get("analytics:active_drivers") or 0)

            avg_price = (
                sum(recent_prices) / len(recent_prices) if recent_prices else 0.0
            )

            # New users in the last 24 hours
            last_24_hours = datetime.utcnow() - timedelta(hours=24)
            new_users = await db.scalar(
                select(func.count(User.id)).where(User.created_at >= last_24_hours)
            )

            # Popular pickup locations
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
                "timestamp": datetime.utcnow().isoformat(),
                "total_bookings": total_bookings,
                "total_revenue": total_revenue,
                "average_price": avg_price,
                "active_drivers": active_drivers,
                "new_users": new_users or 0,
                "popular_pickup_locations": popular_pickup_locations,
            }
            await redis.set("analytics_data", json.dumps(analytics_data))

            logging.info("Analytics computed and stored successfully")
            return "Analytics computed and stored successfully"

        except Exception as e:
            logging.error(f"Error in compute_analytics: {e}")
            self.retry(exc=e)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
async def handle_booking_completion(self, booking_id: int):
    async with AsyncSession(engine) as db:
        try:
            booking = await db.get(Booking, booking_id)
            if not booking:
                logging.error(f"Booking not found for ID: {booking_id}")
                return

            if booking.status in [
                BookingStatusEnum.cancelled,
                BookingStatusEnum.completed,
            ]:
                # Update driver's availability
                driver = await db.get(Driver, booking.driver_id)
                if driver:
                    driver.is_available = True
                    await db.commit()
                    await db.refresh(driver)

                # Update analytics
                await compute_analytics()

            logging.info(f"Handled completion for booking ID: {booking_id}")
            return "Booking completion handled successfully."

        except Exception as e:
            logging.error(f"Error handling booking completion for {booking_id}: {e}")
            self.retry(exc=e)
