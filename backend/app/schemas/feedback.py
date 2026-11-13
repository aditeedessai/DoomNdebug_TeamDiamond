"""Pydantic schemas for project feedback and feedback-to-complaint conversion."""
from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

ComplaintPriority = Literal["Low", "Medium", "High", "Critical"]


class FeedbackBase(BaseModel):
    """Base feedback attributes."""
    category: str = Field(..., min_length=2, max_length=100, description="Feedback issue category")
    message: str = Field(..., min_length=3, max_length=2000, description="Citizen feedback description")


class FeedbackCreate(FeedbackBase):
    """Schema for submitting citizen feedback on a project."""
    project_id: Optional[UUID] = Field(None, description="Referenced project ID (when submitted via /feedback)")


class FeedbackResponse(BaseModel):
    """Schema for feedback data returned to clients."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    project_title: Optional[str] = None
    citizen_id: UUID
    citizen_name: Optional[str] = None
    category: str
    message: str
    created_at: datetime
    complaint_id: Optional[UUID] = Field(None, description="Linked complaint ID if converted")


class FeedbackListResponse(BaseModel):
    """Paginated list of project feedback."""
    items: List[FeedbackResponse]
    total: int


class FeedbackConvertRequest(BaseModel):
    """Schema for converting actionable feedback into a municipal complaint."""
    title: Optional[str] = Field(None, min_length=3, max_length=200, description="Optional custom complaint title")
    priority: Optional[ComplaintPriority] = Field("Medium", description="Triage priority level")
    severity: Optional[int] = Field(5, ge=1, le=10, description="Severity score 1-10")

