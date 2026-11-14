"""Safety Report API routes for citizen submission and restricted official triage.

Task: M4-07 Safety Report Handling
PRD References: Section 4.8, Section 7.5
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user, require_role, require_safety_officer
from app.schemas.profile import ProfileResponse
from app.schemas.safety import (
    SafetyInvestigationUpdate,
    SafetyReportCreate,
    SafetyReportDetailResponse,
    SafetyReportResponse,
)
from app.services.safety_service import safety_service

router = APIRouter()


@router.post(
    "",
    response_model=SafetyReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a safety infrastructure report",
)
async def create_safety_report(
    report_data: SafetyReportCreate,
    current_user: ProfileResponse = Depends(require_role(["citizen"])),
):
    """Citizen submits an unsafe infrastructure or public safety concern.

    Derives citizen_id automatically, forces safety_related=True, and initiates
    AI triage and initial status tracking.
    """
    return await safety_service.create_safety_report(
        citizen=current_user,
        data=report_data,
    )


@router.get(
    "/mine",
    response_model=List[SafetyReportResponse],
    summary="List safety reports submitted by authenticated citizen",
)
async def get_my_safety_reports_mine(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Page offset"),
    current_user: ProfileResponse = Depends(require_role(["citizen"])),
):
    """Retrieve safety reports submitted by the authenticated citizen."""
    return await safety_service.get_my_safety_reports(
        citizen=current_user,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/my",
    response_model=List[SafetyReportResponse],
    summary="List safety reports submitted by authenticated citizen (alias for /mine)",
)
async def get_my_safety_reports_my(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Page offset"),
    current_user: ProfileResponse = Depends(require_role(["citizen"])),
):
    """Retrieve safety reports submitted by the authenticated citizen (alias)."""
    return await safety_service.get_my_safety_reports(
        citizen=current_user,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


@router.get(
    "",
    response_model=List[SafetyReportResponse],
    summary="List restricted safety reports register for designated safety officers",
)
async def list_safety_reports(
    department_id: Optional[UUID] = Query(None, description="Filter by department ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    safety_category: Optional[str] = Query(None, description="Filter by safety category"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Page offset"),
    current_user: ProfileResponse = Depends(require_safety_officer),
):
    """Retrieve safety reports register for designated safety officers only.

    Ordinary officials and workers are forbidden (HTTP 403). Department-scoped
    officers are restricted to reports within their assigned department.
    """
    return await safety_service.list_safety_reports_for_officer(
        officer=current_user,
        department_id=department_id,
        status_filter=status_filter,
        safety_category=safety_category,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{id}",
    response_model=SafetyReportDetailResponse,
    summary="Get single safety report details and chronological timeline",
)
async def get_safety_report_by_id(
    id: UUID,
    current_user: ProfileResponse = Depends(get_current_user),
):
    """Retrieve a single safety report with investigation timeline.

    Citizens can only view their own reports. Designated safety officers can
    view reports within their authorized departmental scope. Ordinary officials
    and workers receive HTTP 403 Forbidden.
    """
    return await safety_service.get_safety_report_by_id(
        report_id=id,
        current_user=current_user,
    )


@router.patch(
    "/{id}",
    response_model=SafetyReportResponse,
    summary="Update safety report investigation status and remarks",
)
async def update_safety_investigation_status(
    id: UUID,
    update_data: SafetyInvestigationUpdate,
    current_user: ProfileResponse = Depends(require_safety_officer),
):
    """Designated safety officers update report lifecycle status or department assignment.

    Validates status transition state machine and records investigation remarks
    in the complaint_updates timeline with compensating rollback on failure.
    """
    return await safety_service.update_safety_investigation_status(
        report_id=id,
        officer=current_user,
        data=update_data,
    )
