"""Pydantic schemas for user profile management."""
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

UserRole = Literal["citizen", "official", "worker"]


class ProfileBase(BaseModel):
    """Base profile attributes."""
    full_name: str = Field(..., description="Full name of the user")
    phone: Optional[str] = Field(None, description="Contact phone number")


class ProfileResponse(ProfileBase):
    """Profile data returned to clients."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: UserRole = "citizen"
    department_id: Optional[UUID] = None
    is_safety_officer: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProfileUpdate(BaseModel):
    """Attributes a user is permitted to update on their own profile."""
    full_name: Optional[str] = None
    phone: Optional[str] = None

