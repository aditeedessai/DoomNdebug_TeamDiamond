"""Pydantic schemas for authentication and registration."""
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.profile import ProfileResponse


class RegisterRequest(BaseModel):
    """Citizen registration request."""
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$", description="Valid user email address")
    password: str = Field(..., min_length=6, description="Password with minimum 6 characters")
    full_name: str = Field(..., min_length=2, description="Citizen full name")
    phone: Optional[str] = Field(None, description="Optional phone number")


class LoginRequest(BaseModel):
    """User credentials login request."""
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$", description="Valid user email address")
    password: str = Field(..., description="User password")


class AuthSession(BaseModel):
    """JWT session information."""
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None


class AuthResponse(BaseModel):
    """Authentication response payload."""
    session: Optional[AuthSession] = None
    profile: ProfileResponse
    message: Optional[str] = None
