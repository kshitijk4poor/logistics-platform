from app.dependencies import get_db
from app.schemas.analytics import AnalyticsCreate, AnalyticsResponse
from app.services.analytics.analytics_service import (
    create_analytics_service,
    get_analytics_service,
)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/analytics", response_model=AnalyticsResponse)
async def create_analytics(data: AnalyticsCreate, db: AsyncSession = Depends(get_db)):
    return await create_analytics_service(data, db)


@router.get("/analytics/{analytics_id}", response_model=AnalyticsResponse)
async def get_analytics(analytics_id: int, db: AsyncSession = Depends(get_db)):
    return await get_analytics_service(analytics_id, db)
