"""
Main API router for Analytics Service v1
"""

from fastapi import APIRouter
from .analytics import router as analytics_router
from .charts import router as charts_router
from .reports import router as reports_router

# Create main v1 router
router = APIRouter(prefix="/api/v1")

# Include all sub-routers
router.include_router(analytics_router)
router.include_router(charts_router)
router.include_router(reports_router)

# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint for Analytics Service"""
    return {
        "status": "healthy",
        "service": "analytics-service",
        "version": "1.0.0"
    }