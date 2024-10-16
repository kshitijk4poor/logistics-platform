import logging

from fastapi import APIRouter, HTTPException

from app.schemas.pricing import PriceResponse, PricingSchema
from app.services.pricing import calculate_price

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post(
    "/price",
    summary="Calculate Estimated Price",
    description="""
Calculate an estimated price for a booking based on various dynamic factors such as distance, time of day, demand, and vehicle type.

### Factors Considered:
- **Base Fare**: Fixed starting price.
- **Distance**: Cost per kilometer between pickup and dropoff locations.
- **Time of Day**: Surge pricing during peak hours.
- **Vehicle Type**: Different pricing for economy, standard, and premium vehicles.

### Edge Cases Handled:
- Identical pickup and dropoff locations.
- Invalid input data.
- Price boundaries enforced (minimum and maximum limits).
""",
    responses={
        200: {
            "description": "Estimated price calculated successfully.",
            "content": {"application/json": {"example": {"estimated_price": 25.50}}},
        },
        400: {
            "description": "Invalid input data.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Pickup and dropoff locations cannot be the same."
                    }
                }
            },
        },
        500: {
            "description": "Internal server error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while calculating the price."
                    }
                }
            },
        },
    },
    response_model=PriceResponse,
)
async def get_price(pricing_data: PricingSchema):
    """
    Endpoint to calculate the estimated price for a booking.

    - **pickup_latitude**: Latitude of the pickup location.
    - **pickup_longitude**: Longitude of the pickup location.
    - **dropoff_latitude**: Latitude of the dropoff location.
    - **dropoff_longitude**: Longitude of the dropoff location.
    - **vehicle_type**: Type of vehicle selected for the booking (economy, standard, premium).
    - **scheduled_time**: (Optional) Scheduled time for the booking in ISO format.
    """
    try:
        price = await calculate_price(pricing_data.dict())
        logger.info(f"Price calculated: {price} for booking: {pricing_data}")
        return {"estimated_price": price}
    except ValueError as ve:
        logger.warning(f"Pricing validation error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Pricing calculation error: {e}")
        raise HTTPException(
            status_code=500, detail="An error occurred while calculating the price."
        )
