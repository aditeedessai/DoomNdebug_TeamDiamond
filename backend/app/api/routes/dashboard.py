"""FastAPI routes for municipal dashboard metrics and analytics.

Task: M4-08 Dashboard APIs (Step 3: Route Implementation)
PRD References: Section 7.7 (Dashboard APIs), Section 14 (Dashboard Cards & Views),
               Section 4.8 (Women's Safety Overview)
"""
from typing import List, Optional, Union
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user, require_official, require_safety_officer
from app.schemas.dashboard import (
    CitizenDashboardResponse,
    DepartmentPerformanceStats,
    OfficialDashboardResponse,
    PriorityBreakdownResponse,
    SafetyDashboardResponse,
    WorkerDashboardResponse,
)
from app.schemas.profile import ProfileResponse
from app.services.dashboard_service import dashboard_service

router = APIRouter()


@router.get(
    "/summary",
    response_model=Union[CitizenDashboardResponse, OfficialDashboardResponse, WorkerDashboardResponse],
    summary="Get role-discriminated dashboard summary",
)
async def get_dashboard_summary(
    department_id: Optional[UUID] = Query(None, description="Filter metrics by department (officials only)"),
    current_user: ProfileResponse = Depends(get_current_user),
):
    """Retrieve role-specific dashboard metrics and preview cards.

    - Citizens receive personal complaint counts and public municipal activity indicators.
    - Officials receive city-wide or department-scoped overview cards and backlogs.
    - Workers receive assigned task counts and active assignment previews.
    """
    return await dashboard_service.get_summary(current_user, department_id=department_id)


@router.get(
    "/departments",
    response_model=List[DepartmentPerformanceStats],
    summary="Get department performance statistics",
)
async def get_department_performance_stats(
    department_id: Optional[UUID] = Query(None, description="Filter statistics by department ID"),
    current_user: ProfileResponse = Depends(require_official),
):
    """Retrieve department-level complaint counts and resolution rates.

    Restricted to officials. Department-scoped officials are restricted to their own department.
    """
    return await dashboard_service.get_department_stats(current_user, department_id=department_id)


@router.get(
    "/priorities",
    response_model=PriorityBreakdownResponse,
    summary="Get complaint priority breakdown",
)
async def get_priority_distribution(
    department_id: Optional[UUID] = Query(None, description="Filter breakdown by department ID"),
    current_user: ProfileResponse = Depends(require_official),
):
    """Retrieve distribution of complaints across priority levels (Critical, High, Medium, Low).

    Restricted to officials. Ordinary officials exclude safety-related reports.
    """
    return await dashboard_service.get_priority_breakdown(current_user, department_id=department_id)


@router.get(
    "/safety",
    response_model=SafetyDashboardResponse,
    summary="Get safety incident dashboard overview",
)
async def get_safety_dashboard_overview(
    current_user: ProfileResponse = Depends(require_safety_officer),
):
    """Retrieve aggregated safety report metrics and category breakdown.

    Restricted exclusively to designated safety officers.
    """
    return await dashboard_service.get_safety_summary(current_user)
