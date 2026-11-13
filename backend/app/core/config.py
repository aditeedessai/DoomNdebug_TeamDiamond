"""Centralized application settings using Pydantic Settings."""
import json
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Core Application Settings
    PROJECT_NAME: str = "AI City Management Platform API"
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api/v1"

    # CORS Settings (supports comma-separated string, JSON array, or list of strings)
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS origins from a comma-separated string, JSON array, or list."""
        if isinstance(v, str):
            v_trimmed = v.strip()
            if v_trimmed.startswith("[") and v_trimmed.endswith("]"):
                try:
                    parsed = json.loads(v_trimmed)
                    if isinstance(parsed, list):
                        return [str(origin).strip() for origin in parsed if str(origin).strip()]
                except json.JSONDecodeError:
                    pass
            # Split comma-separated string
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return [str(origin).strip() for origin in v if str(origin).strip()]
        return ["http://localhost:5173", "http://localhost:3000"]

    # Supabase Credentials (optional during skeleton setup; startup will not fail if omitted)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # Gemini AI Credentials (optional during skeleton setup; coordinated with Member 3)
    GEMINI_API_KEY: str = ""


# Reusable singleton instance
settings = Settings()
