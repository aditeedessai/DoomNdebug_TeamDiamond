"""FastAPI routes for municipal field worker directory and profiles.

Task: M4-09 Worker and Officer Assignments (Step 4: Route Implementation)
PRD References: Section 4.7 (Field Worker Assignment), Section 6.7 (workers),
               Section 7.6 (Workers and assignments APIs)
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status

from app.api.deps import require_role
from app.schemas.assignment import WorkerAvailability, WorkerResponse
from app.schemas.profile import ProfileResponse
from app.services.assignment_service import assignment_service

router = APIRouter()


@router.get(
    "",
    response_model=List[WorkerResponse],
    summary="List municipal field workers",
)
async def list_workers(
    department_id: Optional[UUID] = Query(None, description="Filter workers by department (officials only)"),
    availability: Optional[WorkerAvailability] = Query(None, description="Filter workers by availability status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    current_user: ProfileResponse = Depends(require_role(["official", "worker"])),
):
    """Retrieve municipal field workers within authorized scope.

    - Officials view workers within their authorized department scope (or municipal-wide if unassigned).
    - Department-scoped officials cannot override their department restriction via query parameters.
    - Workers receive only their own worker profile.
    - Citizens are denied access with HTTP 403.
    """
    avail_str = availability if availability else None
    return await assignment_service.list_workers(
        user=current_user,
        department_id=department_id,
        availability=avail_str,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{worker_id}",
    response_model=WorkerResponse,
    summary="Get worker profile by ID",
)
async def get_worker_by_id(
    worker_id: UUID,
    current_user: ProfileResponse = Depends(require_role(["official", "worker"])),
):
    """Retrieve a specific worker profile by UUID.

    - Officials can view workers within their department scope.
    - Workers can view only their own worker profile.
    - Citizens are denied access with HTTP 403.
    """
    return await assignment_service.get_worker_by_id(
        user=current_user,
        worker_id=worker_id,
    )

