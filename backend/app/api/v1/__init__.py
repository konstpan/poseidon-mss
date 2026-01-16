"""API v1 router aggregation.

Combines all v1 API routers into a single router for mounting.
"""

from fastapi import APIRouter

from app.api.v1.vessels import router as vessels_router
from app.api.v1.zones import router as zones_router

# Create v1 router
router = APIRouter()

# Include sub-routers
router.include_router(vessels_router)
router.include_router(zones_router)

__all__ = ["router"]
