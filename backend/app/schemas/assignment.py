"""Pydantic schemas for municipal field workers, teams, and task assignments.

Task: M4-09 Worker and Officer Assignments (Step 2: Schemas)
PRD References: Section 4.7 (Field Worker Assignment), Section 6.7 (workers table),
               Section 6.8 (assignments table), Section 7.6 (Workers and assignments APIs)
Database References: database/schema.sql (workers, assignments, chk_assignment_target)
"""
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

# Canonical assignment status strictly matching public.assignments in database/schema.sql
AssignmentStatus = Literal["Assigned", "In Progress", "Completed"]

# Canonical worker availability strictly matching public.workers in database/schema.sql
WorkerAvailability = Literal["Available", "Busy", "Unavailable"]


class WorkerResponse(BaseModel):
    """Schema representing a municipal field worker or rapid response crew."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    profile_id: Optional[UUID] = Field(None, description="Linked user profile UUID if authenticated worker")
    name: str = Field(..., description="Worker or field team crew name")
    department_id: UUID = Field(..., description="Assigned municipal department UUID")
    department_name: Optional[str] = Field(None, description="Resolved municipal department name")
    availability: WorkerAvailability = Field("Available", description="Current field availability status")
    phone: Optional[str] = Field(None, description="Contact phone number")
    created_at: datetime
    updated_at: datetime


class AssignmentCreate(BaseModel):
    """Schema for an official dispatching a task to a field worker.

    Enforces the single-target database rule: exactly one of complaint_id or hotspot_id.
    """
    model_config = ConfigDict(extra="forbid")

    complaint_id: Optional[UUID] = Field(None, description="Target municipal complaint UUID")
    hotspot_id: Optional[UUID] = Field(None, description="Target traffic hotspot UUID")
    worker_id: UUID = Field(..., description="Assigned field worker or crew UUID")
    task_description: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Detailed instructions for the assigned field task",
    )
    status: AssignmentStatus = Field("Assigned", description="Initial assignment status")

    @model_validator(mode="after")
    def validate_exact_single_target(self) -> "AssignmentCreate":
        """Enforce database check constraint chk_assignment_target."""
        has_complaint = self.complaint_id is not None
        has_hotspot = self.hotspot_id is not None

        if has_complaint and has_hotspot:
            raise ValueError(
                "Invalid assignment target: Cannot assign both a complaint and a traffic hotspot. Exactly one target must be specified."
            )
        if not has_complaint and not has_hotspot:
            raise ValueError(
                "Invalid assignment target: Must specify either a complaint_id or a hotspot_id. Neither target was provided."
            )
        return self


class AssignmentUpdate(BaseModel):
    """Schema for updating task status, instructions, notes, or reassignment.

    Reject empty update requests and unknown/immutable fields.
    """
    model_config = ConfigDict(extra="forbid")

    status: Optional[AssignmentStatus] = Field(None, description="Updated assignment task status")
    task_description: Optional[str] = Field(
        None,
        min_length=3,
        max_length=1000,
        description="Updated task notes or instructions",
    )
    worker_id: Optional[UUID] = Field(
        None,
        description="Reassigned worker or field team UUID (Officials only)",
    )
    notes: Optional[str] = Field(
        None,
        max_length=1000,
        description="Field progress remarks or completion notes",
    )

    @model_validator(mode="after")
    def validate_non_empty_update(self) -> "AssignmentUpdate":
        """Ensure at least one mutable field is provided."""
        if (
            self.status is None
            and self.task_description is None
            and self.worker_id is None
            and self.notes is None
        ):
            raise ValueError(
                "AssignmentUpdate request body cannot be empty. At least one field (status, task_description, worker_id, notes) must be provided."
            )
        return self


class AssignmentResponse(BaseModel):
    """Schema representing an assignment record."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    complaint_id: Optional[UUID] = Field(None, description="Linked complaint UUID if applicable")
    hotspot_id: Optional[UUID] = Field(None, description="Linked traffic hotspot UUID if applicable")
    worker_id: Optional[UUID] = Field(None, description="Assigned field worker UUID")
    worker_name: Optional[str] = Field(None, description="Assigned field worker or crew name")
    officer_id: UUID = Field(..., description="Assigning official profile UUID")
    officer_name: Optional[str] = Field(None, description="Assigning official full name")
    task_description: str = Field(..., description="Field task notes or instructions")
    status: AssignmentStatus = Field(..., description="Current assignment lifecycle status")
    created_at: datetime
    updated_at: datetime


class AssignmentDetailResponse(AssignmentResponse):
    """Detailed assignment representation including resolved target metadata."""
    target_type: Literal["complaint", "hotspot"] = Field(..., description="Discriminator for the assignment target entity")
    complaint_title: Optional[str] = Field(None, description="Title of target complaint if target_type is complaint")
    complaint_category: Optional[str] = Field(None, description="Category of target complaint")
    complaint_priority: Optional[str] = Field(None, description="Priority level of target complaint")
    hotspot_congestion: Optional[str] = Field(None, description="Congestion level if target_type is hotspot")
    hotspot_description: Optional[str] = Field(None, description="Context description if target_type is hotspot")

