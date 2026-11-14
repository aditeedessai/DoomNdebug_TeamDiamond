"""FastAPI routes for municipal task assignments and field worker dispatch.

Task: M4-09 Worker and Officer Assignments (Step 4: Route Implementation)
PRD References: Section 4.7 (Field Worker Assignment), Section 6.8 (assignments),
               Section 7.6 (Workers and assignments APIs)
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status

from app.api.deps import require_official, require_role
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentDetailResponse,
    AssignmentResponse,
    AssignmentStatus,
    AssignmentUpdate,
)
from app.schemas.profile import ProfileResponse
from app.services.assignment_service import assignment_service

router = APIRouter()


@router.post(
    "",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create field task assignment",
)
async def create_assignment(
    data: AssignmentCreate,
    current_user: ProfileResponse = Depends(require_official),
):
    """Create a task assignment for a civic complaint or traffic hotspot.

    - Restricted to authorized municipal officials.
    - Officer identity is derived strictly from the authenticated profile.
    - Single target constraint enforced: exactly one of complaint_id or hotspot_id.
    - Automatically advances complaint status to 'Assigned' and logs timeline history.
    - Hotspot assignments are isolated and do not log complaint timeline events.
    """
    return await assignment_service.create_assignment(
        official=current_user,
        data=data,
    )


@router.get(
    "",
    response_model=List[AssignmentResponse],
    summary="List task assignments",
)
async def list_assignments(
    complaint_id: Optional[UUID] = Query(None, description="Filter assignments by complaint UUID"),
    hotspot_id: Optional[UUID] = Query(None, description="Filter assignments by traffic hotspot UUID"),
    worker_id: Optional[UUID] = Query(None, description="Filter assignments by worker UUID (officials only)"),
    department_id: Optional[UUID] = Query(None, description="Filter assignments by department UUID (officials only)"),
    status: Optional[AssignmentStatus] = Query(None, description="Filter assignments by task status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    current_user: ProfileResponse = Depends(require_role(["official", "worker"])),
):
    """Retrieve task assignments within authorized role and department scope.

    - Officials view assignments within their authorized department (or municipal-wide if unassigned).
    - Ordinary officials are strictly screened out from safety report assignments.
    - Workers view only their own assigned tasks.
    - Citizens are denied access with HTTP 403.
    """
    st_val = status if status else None
    return await assignment_service.list_assignments(
        user=current_user,
        status_filter=st_val,
        complaint_id=complaint_id,
        hotspot_id=hotspot_id,
        worker_id=worker_id,
        department_id=department_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{assignment_id}",
    response_model=AssignmentDetailResponse,
    summary="Get assignment details",
)
async def get_assignment_by_id(
    assignment_id: UUID,
    current_user: ProfileResponse = Depends(require_role(["official", "worker"])),
):
    """Retrieve assignment details with enriched complaint or hotspot metadata.

    - Officials can view assignments within their authorized department scope.
    - Ordinary officials are denied access to safety report assignments.
    - Workers can view only their own task assignments.
    - Citizens are denied access with HTTP 403.
    """
    return await assignment_service.get_assignment_by_id(
        user=current_user,
        assignment_id=assignment_id,
    )


@router.patch(
    "/{assignment_id}",
    response_model=AssignmentResponse,
    summary="Update task assignment status or details",
)
async def update_assignment(
    assignment_id: UUID,
    data: AssignmentUpdate,
    current_user: ProfileResponse = Depends(require_role(["official", "worker"])),
):
    """Update assignment status, task instructions, notes, or worker reassignment.

    - Officials can update status, instructions, and reassign eligible workers within scope.
    - Workers can update only their own task status and progress/completion notes.
    - Workers are forbidden from reassigning workers or editing task instructions.
    - Completed assignments are terminal and cannot be reopened.
    - Status transitions synchronize complaint lifecycle and log timeline history.
    """
    return await assignment_service.update_assignment(
        user=current_user,
        assignment_id=assignment_id,
        data=data,
    )

