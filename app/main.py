from fastapi import FastAPI

from app.routes import (
    admin,
    analytics,
    bookings,
    drivers,
    pricing,
    tracking,
    websockets,
)

app = FastAPI()

app.include_router(admin.router, prefix="/api/v1", tags=["admin"])
app.include_router(bookings.router, prefix="/api/v1", tags=["bookings"])
app.include_router(tracking.router, prefix="/api/v1", tags=["tracking"])
app.include_router(pricing.router, prefix="/api/v1", tags=["pricing"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
app.include_router(drivers.router, prefix="/api/v1", tags=["drivers"])
app.include_router(websockets.router, prefix="/api/v1", tags=["websockets"])


@app.get("/")
async def root():
    return {"message": "Welcome to the Logistics Platform API"}
