"""API route definitions and modular router aggregation."""
from fastapi import APIRouter

from app.api.routes import auth, complaints

api_router = APIRouter()

# Health route
@api_router.get("/health", tags=["health"], summary="API v1 Health Check")
async def api_v1_health():
    """Versioned health check endpoint for API v1."""
    return {
        "status": "ok",
        "version": "1.0.0"
    }

# Authentication routes
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Complaint routes
api_router.include_router(complaints.router, prefix="/complaints", tags=["complaints"])
