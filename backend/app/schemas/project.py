"""Pydantic schemas for municipal infrastructure projects."""
from datetime import date, datetime
from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

ProjectStatus = Literal["Planned", "Ongoing", "Completed"]


class ProjectBase(BaseModel):
    """Base schema for municipal projects."""
    title: str = Field(..., min_length=3, max_length=200, description="Project title or name")
    description: str = Field(..., min_length=5, description="Detailed description of the project scope")
    department_id: UUID = Field(..., description="Responsible municipal department ID")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Project location latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Project location longitude")
    start_date: date = Field(..., description="Project commencement date")
    expected_end_date: date = Field(..., description="Target completion date")


class ProjectCreate(ProjectBase):
    """Schema for project creation by authorized officials."""
    status: Optional[str] = Field("Planned", description="Initial project status (Planned, Ongoing, Completed)")
    is_published: Optional[bool] = Field(False, description="Public visibility flag (default false for draft)")

    @model_validator(mode="after")
    def validate_dates(self) -> "ProjectCreate":
        if self.expected_end_date < self.start_date:
            raise ValueError("expected_end_date cannot be earlier than start_date")
        return self


class ProjectUpdate(BaseModel):
    """Schema for updating project details by authorized officials."""
    title: Optional[str] = Field(None, min_length=3, max_length=200, description="Updated project title")
    description: Optional[str] = Field(None, min_length=5, description="Updated description")
    department_id: Optional[UUID] = Field(None, description="Target municipal department ID")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Updated latitude")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Updated longitude")
    start_date: Optional[date] = Field(None, description="Updated start date")
    expected_end_date: Optional[date] = Field(None, description="Updated target completion date")
    status: Optional[str] = Field(None, description="Updated project lifecycle status (Planned, Ongoing, Completed)")
    is_published: Optional[bool] = Field(None, description="Updated publication visibility")

    @model_validator(mode="after")
    def validate_dates_if_both_present(self) -> "ProjectUpdate":
        if self.start_date and self.expected_end_date:
            if self.expected_end_date < self.start_date:
                raise ValueError("expected_end_date cannot be earlier than start_date")
        return self


class ProjectResponse(BaseModel):
    """Schema for project data returned to clients."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    department_id: UUID
    department_name: Optional[str] = None
    latitude: float
    longitude: float
    start_date: date
    expected_end_date: date
    status: str
    is_published: bool
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    """Paginated list of municipal projects."""
    items: List[ProjectResponse]
    total: int
