from app.dependencies import get_db
from app.schemas.pricing import PricingCreate, PricingResponse
from app.services.pricing.pricing_service import (
    create_pricing_service,
    get_pricing_service,
)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/pricing", response_model=PricingResponse)
async def create_pricing(data: PricingCreate, db: AsyncSession = Depends(get_db)):
    return await create_pricing_service(data, db)


@router.get("/pricing/{pricing_id}", response_model=PricingResponse)
async def get_pricing(pricing_id: int, db: AsyncSession = Depends(get_db)):
    return await get_pricing_service(pricing_id, db)
