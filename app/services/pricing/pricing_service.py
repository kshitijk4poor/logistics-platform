from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Pricing
from app.schemas.pricing import PricingCreate, PricingResponse


async def create_pricing_service(
    data: PricingCreate, db: AsyncSession
) -> PricingResponse:
    pricing = Pricing(
        vehicle_type=data.vehicle_type,
        base_fare=data.base_fare,
        cost_per_km=data.cost_per_km,
    )
    db.add(pricing)
    await db.commit()
    await db.refresh(pricing)
    return pricing


async def get_pricing_service(pricing_id: int, db: AsyncSession) -> PricingResponse:
    pricing = await db.get(Pricing, pricing_id)
    if not pricing:
        raise HTTPException(status_code=404, detail="Pricing not found")
    return pricing
