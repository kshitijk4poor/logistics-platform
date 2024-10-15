import asyncio
import logging

import jsonlog
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.models import Role, RoleEnum
from app.routes import (
    admin,
    analytics,
    bookings,
    drivers,
    pricing,
    tracking,
    users,
    websockets,
)
from app.services.websocket_service import manager
from app.tasks.demand import update_demand
from db.database import async_session, engine
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")
logger.addHandler(jsonlog.JSONFormatter())

app = FastAPI()

app.add_middleware(RateLimiterMiddleware)

app.include_router(admin.router, prefix="/api/v1", tags=["admin"])
app.include_router(bookings.router, prefix="/api/v1", tags=["bookings"])
app.include_router(tracking.router, prefix="/api/v1", tags=["tracking"])
app.include_router(pricing.router, prefix="/api/v1", tags=["pricing"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
app.include_router(drivers.router, prefix="/api/v1", tags=["drivers"])
app.include_router(websockets.router, prefix="/api/v1", tags=["websockets"])
app.include_router(users.router, prefix="/api/v1", tags=["users"])  # Add this line

instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)


async def create_roles():
    async with async_session() as session:
        async with session.begin():
            for role_name in RoleEnum:
                result = await session.execute(
                    select(Role).where(Role.name == role_name)
                )
                role = result.scalar_one_or_none()
                if not role:
                    session.add(Role(name=role_name))
        await session.commit()
    logger.info("Roles ensured.")


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(update_demand())
    await create_roles()


@app.get("/")
async def root():
    return {"message": "Welcome to the Logistics Platform API"}
