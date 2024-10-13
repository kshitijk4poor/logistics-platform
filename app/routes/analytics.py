import json
from datetime import datetime, timedelta, timezone

import aioredis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_admin
from app.schemas.analytics import AnalyticsResponse, PopularPickupLocation
from db.database import get_db

router = APIRouter()

REDIS_KEY = "analytics_data"


async def get_redis_client():
    return await aioredis.from_url("redis://localhost", decode_responses=True)


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(current_admin=Depends(get_current_admin)):
    """
    Fetches precomputed analytics data from Redis.
    If the data does not exist or cannot be read, it raises an HTTP 500 error.
    """
    redis = await get_redis_client()
    try:
        analytics_data = await redis.get(REDIS_KEY)
        if analytics_data is None:
            raise HTTPException(
                status_code=500,
                detail="Analytics data not found. Please try again later.",
            )

        analytics_data = json.loads(analytics_data)

        popular_pickup_locations = [
            PopularPickupLocation(location=loc["pickup_location"], count=loc["count"])
            for loc in analytics_data.get("popular_pickup_locations", [])
        ]

        return AnalyticsResponse(
            total_bookings=analytics_data.get("total_bookings", 0),
            total_revenue=analytics_data.get("total_revenue", 0.0),
            average_price=analytics_data.get("average_price", 0.0),
            popular_pickup_locations=popular_pickup_locations,
            active_drivers=analytics_data.get("active_drivers", 0),
            new_users=analytics_data.get("new_users", 0),
        )

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error reading analytics data.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
    finally:
        await redis.close()
