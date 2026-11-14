"""API route definitions and modular router aggregation."""
from fastapi import APIRouter

from app.api.routes import auth, complaints, feedback, map, projects, safety

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

# Project routes
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])

# Feedback routes
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])

# Map and traffic routes
api_router.include_router(map.router, prefix="/map", tags=["map"])

# Safety report routes
api_router.include_router(safety.router, prefix="/safety-reports", tags=["safety-reports"])
