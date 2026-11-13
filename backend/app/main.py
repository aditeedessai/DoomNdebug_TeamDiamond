"""FastAPI Application entrypoint for AI City Management Platform."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import api_router


def create_application() -> FastAPI:
    """Application factory for FastAPI service."""
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
    )

    # Configure CORS middleware
    # Strip any trailing slashes from origins for precise match
    allowed_origins = [str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS]

    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Root health check endpoint
    @application.get("/health", tags=["health"], summary="Root Health Check")
    async def root_health():
        return {
            "status": "ok",
            "version": "1.0.0"
        }

    # Mount versioned modular API router (/api/v1)
    application.include_router(api_router, prefix=settings.API_V1_STR)

    return application


app = create_application()

