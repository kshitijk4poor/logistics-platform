import json
from datetime import datetime, timedelta

from celery import Celery
from sqlalchemy import func

from db.database import SessionLocal
from app.models import Booking, Driver, User

app = Celery("tasks", broker="redis://localhost:6379/0")


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(3600.0, compute_analytics.s(), name="compute every hour")


@app.task
def compute_analytics():
    db = SessionLocal()
    try:
        now = datetime.now()
        last_24_hours = now - timedelta(hours=24)

        # Compute hourly analytics for the last 24 hours
        hourly_data = []
        for hour in range(24):
            start_time = last_24_hours + timedelta(hours=hour)
            end_time = start_time + timedelta(hours=1)

            bookings_count = (
                db.query(func.count(Booking.id))
                .filter(Booking.date.between(start_time, end_time))
                .scalar()
            )
            revenue = (
                db.query(func.sum(Booking.price))
                .filter(Booking.date.between(start_time, end_time))
                .scalar()
            )

            hourly_data.append(
                {
                    "hour": start_time.strftime("%Y-%m-%d %H:00"),
                    "bookings": bookings_count,
                    "revenue": float(revenue) if revenue else 0,
                }
            )

        # Compute overall analytics
        total_bookings = (
            db.query(func.count(Booking.id)).filter(Booking.date >= last_24_hours).scalar()
        )
        total_revenue = (
            db.query(func.sum(Booking.price)).filter(Booking.date >= last_24_hours).scalar()
        )
        avg_price = (
            db.query(func.avg(Booking.price)).filter(Booking.date >= last_24_hours).scalar()
        )
        active_drivers = (
            db.query(func.count(Driver.id)).filter(Driver.is_available == True).scalar()
        )
        new_users = (
            db.query(func.count(User.id)).filter(User.created_at >= last_24_hours).scalar()
        )

        analytics_data = {
            "timestamp": now.isoformat(),
            "total_bookings": total_bookings,
            "total_revenue": float(total_revenue) if total_revenue else 0,
            "average_price": float(avg_price) if avg_price else 0,
            "active_drivers": active_drivers,
            "new_users": new_users,
            "hourly_data": hourly_data,
        }

        # Store analytics data (you might want to use a database or a file for this)
        with open("analytics_data.json", "w") as f:
            json.dump(analytics_data, f)
        return "Analytics computed and stored successfully"

    except Exception as e:
        print(f"Error in compute_analytics: {e}")
        raise
    finally:
        db.close()
