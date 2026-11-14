"""Pydantic schemas for municipal dashboard summaries and analytics.

Task: M4-08 Dashboard APIs (Step 1: Schemas)
PRD References: Section 7.7 (Dashboard APIs), Section 14 (Dashboard Cards & Views),
               Section 4.8 (Women's Safety Overview)
Database Reference: database/schema.sql (assignments.status CHECK constraint)
"""
from datetime import datetime
from typing import Dict, List, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, conint

from app.schemas.complaint import ComplaintPriority, ComplaintStatus

# Canonical assignment status values strictly matching public.assignments in database/schema.sql
AssignmentStatus = Literal["Assigned", "In Progress", "Completed"]


class RecentComplaintItem(BaseModel):
    """Concise representation of a recent complaint for dashboard previews."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    category: str
    status: ComplaintStatus
    priority: ComplaintPriority
    created_at: datetime


class RecentTaskItem(BaseModel):
    """Concise representation of an assigned work task for worker dashboard."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_description: str
    status: AssignmentStatus
    created_at: datetime


class CitizenDashboardResponse(BaseModel):
    """Personalized dashboard metrics and previews for citizen users."""
    model_config = ConfigDict(from_attributes=True)

    my_total: int = Field(0, ge=0, description="Total complaints submitted by authenticated citizen")
    my_pending: int = Field(0, ge=0, description="Complaints awaiting triage or review")
    my_in_progress: int = Field(0, ge=0, description="Complaints currently undergoing active repair")
    my_resolved: int = Field(0, ge=0, description="Successfully resolved complaints")
    my_rejected: int = Field(0, ge=0, description="Rejected or invalid submissions")
    active_projects: int = Field(0, ge=0, description="Count of active published municipal projects")
    traffic_hotspots: int = Field(0, ge=0, description="Count of active traffic congestion hotspots")
    recent_complaints: List[RecentComplaintItem] = Field(
        default_factory=list,
        description="Latest complaints submitted by authenticated citizen",
    )


class OfficialDashboardResponse(BaseModel):
    """Municipal summary cards and recent activity for municipal officials."""
    model_config = ConfigDict(from_attributes=True)

    total_complaints: int = Field(0, ge=0, description="Total complaints in municipal/department scope")
    pending_complaints: int = Field(0, ge=0, description="Complaints awaiting assignment or triage")
    in_progress_complaints: int = Field(0, ge=0, description="Complaints with active repairs underway")
    resolved_complaints: int = Field(0, ge=0, description="Resolved civic complaints")
    high_priority_complaints: int = Field(0, ge=0, description="Urgent complaints (High or Critical priority)")
    department_backlog: int = Field(0, ge=0, description="Unresolved complaint backlog")
    traffic_hotspots: int = Field(0, ge=0, description="Count of active traffic congestion hotspots")
    recent_complaints: List[RecentComplaintItem] = Field(
        default_factory=list,
        description="Latest complaints within official's authorized scope",
    )


class WorkerDashboardResponse(BaseModel):
    """Task assignment summary for field workers."""
    model_config = ConfigDict(from_attributes=True)

    total_assigned_tasks: int = Field(0, ge=0, description="Total task assignments for authenticated worker")
    pending_tasks: int = Field(0, ge=0, description="Tasks awaiting action (status: Assigned)")
    in_progress_tasks: int = Field(0, ge=0, description="Active field tasks (status: In Progress)")
    completed_tasks: int = Field(0, ge=0, description="Completed assignments (status: Completed)")
    recent_tasks: List[RecentTaskItem] = Field(
        default_factory=list,
        description="Latest task assignments for authenticated worker",
    )


class DepartmentPerformanceStats(BaseModel):
    """Performance and resolution statistics for a municipal department."""
    model_config = ConfigDict(from_attributes=True)

    department_id: UUID
    department_name: str
    total_complaints: int = Field(0, ge=0, description="Total complaints assigned to this department")
    pending_complaints: int = Field(0, ge=0, description="Pending or unassigned department complaints")
    in_progress_complaints: int = Field(0, ge=0, description="Complaints currently undergoing active repair")
    resolved_complaints: int = Field(0, ge=0, description="Successfully resolved complaints")
    resolution_rate: float = Field(
        0.0,
        ge=0.0,
        le=100.0,
        description="Percentage of resolved complaints (0.0 to 100.0)",
    )


class PriorityBreakdownResponse(BaseModel):
    """Breakdown of complaints across priority levels."""
    model_config = ConfigDict(from_attributes=True)

    critical: int = Field(0, ge=0, description="Count of Critical priority complaints")
    high: int = Field(0, ge=0, description="Count of High priority complaints")
    medium: int = Field(0, ge=0, description="Count of Medium priority complaints")
    low: int = Field(0, ge=0, description="Count of Low priority complaints")
    total: int = Field(0, ge=0, description="Total complaints across all priorities")


class SafetyDashboardResponse(BaseModel):
    """Aggregated safety incident metrics for designated safety officers."""
    model_config = ConfigDict(from_attributes=True)

    total_safety_reports: int = Field(0, ge=0, description="Total safety infrastructure reports")
    pending_investigations: int = Field(0, ge=0, description="Safety reports awaiting inspection or review")
    in_progress_investigations: int = Field(0, ge=0, description="Active safety inspections underway")
    resolved_investigations: int = Field(0, ge=0, description="Resolved safety concerns")
    high_severity_count: int = Field(0, ge=0, description="Reports with physical hazard severity rating >= 7")
    category_breakdown: Dict[str, conint(ge=0)] = Field(
        default_factory=dict,
        description="Counts of safety concerns grouped by safety category (values >= 0)",
    )
