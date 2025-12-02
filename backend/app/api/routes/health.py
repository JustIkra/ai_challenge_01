"""
Health check endpoint for monitoring service status.
"""

from fastapi import APIRouter, status
from pydantic import BaseModel


router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    service: str
    version: str


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["health"],
    summary="Health check",
    description="Check if the service is running and healthy",
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint that returns service status.

    Returns:
        HealthResponse: Service health status information
    """
    return HealthResponse(
        status="healthy",
        service="day1-backend",
        version="0.1.0",
    )
