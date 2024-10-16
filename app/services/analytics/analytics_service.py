from app.models import Analytics
from app.schemas.analytics import AnalyticsCreate, AnalyticsResponse
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession


async def create_analytics_service(
    data: AnalyticsCreate, db: AsyncSession
) -> AnalyticsResponse:
    analytics = Analytics(metric=data.metric, value=data.value)
    db.add(analytics)
    await db.commit()
    await db.refresh(analytics)
    return analytics


async def get_analytics_service(
    analytics_id: int, db: AsyncSession
) -> AnalyticsResponse:
    analytics = await db.get(Analytics, analytics_id)
    if not analytics:
        raise HTTPException(status_code=404, detail="Analytics not found")
    return analytics
