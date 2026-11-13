"""Pydantic schemas for Complaint CRUD and Image Upload."""
from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

ComplaintStatus = Literal[
    "Submitted",
    "Under Review",
    "Assigned",
    "In Progress",
    "Resolved",
    "Rejected",
    "Needs More Information",
]

ComplaintPriority = Literal["Low", "Medium", "High", "Critical"]


class ComplaintCreate(BaseModel):
    """Schema for creating a new complaint by a citizen."""
    title: str = Field(..., min_length=3, max_length=200, description="Brief summary of the issue")
    description: str = Field(..., min_length=5, description="Detailed description of the issue")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Geographic latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Geographic longitude")
    category: str = Field(..., min_length=2, description="Issue category (e.g., Road Infrastructure, Sanitation)")
    issue_type: str = Field(..., min_length=2, description="Specific issue type (e.g., Pothole, Water Leakage)")
    image_url: Optional[str] = Field(None, description="Storage path or URL of uploaded image")
    safety_related: bool = Field(False, description="Whether this report concerns infrastructure safety")
    safety_category: Optional[str] = Field(None, description="Type of safety concern (e.g., Poor Lighting, Deserted Bus Stop)")


class ComplaintUpdate(BaseModel):
    """Schema for updating an existing complaint by the submitting citizen.

    Only permitted while status is 'Submitted' or 'Needs More Information'.
    """
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, min_length=5)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    category: Optional[str] = Field(None, min_length=2)
    issue_type: Optional[str] = Field(None, min_length=2)
    image_url: Optional[str] = None
    safety_related: Optional[bool] = None
    safety_category: Optional[str] = None


class OfficialStatusUpdate(BaseModel):
    """Schema for updating complaint status and assignment by an official."""
    status: ComplaintStatus = Field(..., description="New complaint status")
    remarks: str = Field(..., min_length=3, description="Official remarks explaining the update")
    department_id: Optional[UUID] = Field(None, description="Assigned department ID")
    priority: Optional[ComplaintPriority] = Field(None, description="Updated priority level")
    severity: Optional[int] = Field(None, ge=1, le=10, description="Updated severity rating 1-10")


class ComplaintUpdateItem(BaseModel):
    """Schema for a single status update history record."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    complaint_id: UUID
    actor_id: UUID
    actor_name: Optional[str] = None
    status: str
    remarks: str
    created_at: datetime


class ComplaintResponse(BaseModel):
    """Schema for standard complaint representation."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    citizen_id: UUID
    citizen_name: Optional[str] = None
    title: str
    description: str
    image_url: Optional[str] = None
    image_signed_url: Optional[str] = None
    latitude: float
    longitude: float
    category: str
    issue_type: str
    department_id: Optional[UUID] = None
    department_name: Optional[str] = None
    severity: int = 5
    priority: ComplaintPriority = "Medium"
    status: ComplaintStatus = "Submitted"
    master_incident_id: Optional[UUID] = None
    report_count: int = 1
    safety_related: bool = False
    safety_category: Optional[str] = None
    ai_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ComplaintDetailResponse(ComplaintResponse):
    """Detailed complaint view including the timeline of updates."""
    updates: List[ComplaintUpdateItem] = []


class ImageUploadResponse(BaseModel):
    """Response returned upon successful photograph upload."""
    image_path: str = Field(..., description="Storage object path stored in complaint record")
    file_name: str
    content_type: str
    size_bytes: int
    signed_url: Optional[str] = None

