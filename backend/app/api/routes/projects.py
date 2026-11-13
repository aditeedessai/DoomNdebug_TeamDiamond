"""API route endpoints for municipal projects and project-scoped feedback."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user, require_role
from app.schemas.complaint import ComplaintResponse
from app.schemas.feedback import FeedbackConvertRequest, FeedbackCreate, FeedbackResponse
from app.schemas.profile import ProfileResponse
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.feedback_service import feedback_service
from app.services.project_service import project_service

router = APIRouter()


@router.get(
    "",
    response_model=List[ProjectResponse],
    summary="List municipal projects",
)
async def list_projects(
    department_id: Optional[UUID] = Query(None, description="Filter by municipal department ID"),
    status: Optional[str] = Query(None, description="Filter by project lifecycle status (Planned, Ongoing, Completed)"),
    is_published: Optional[bool] = Query(None, description="Filter by publication visibility (Officials only)"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: ProfileResponse = Depends(get_current_user),
):
    """Retrieve municipal projects.

    Citizens and workers can only retrieve published projects.
    Officials can view all projects or filter by publication state and department.
    """
    return await project_service.list_projects(
        current_user=current_user,
        department_id=department_id,
        status_filter=status,
        is_published=is_published,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create municipal project (Officials only)",
)
async def create_project(
    data: ProjectCreate,
    current_user: ProfileResponse = Depends(require_role(["official"])),
):
    """Create a new municipal project.

    Restricted to authorized officials. Validates department ID, date consistency,
    and department boundary permissions.
    """
    return await project_service.create_project(
        official=current_user,
        data=data,
    )


@router.get(
    "/{id}",
    response_model=ProjectResponse,
    summary="Retrieve individual project details",
)
async def get_project(
    id: UUID,
    current_user: ProfileResponse = Depends(get_current_user),
):
    """Retrieve details of an individual municipal project.

    Citizens only have access to published projects. Unpublished drafts return HTTP 404.
    """
    return await project_service.get_project_by_id(
        project_id=id,
        current_user=current_user,
    )


@router.patch(
    "/{id}",
    response_model=ProjectResponse,
    summary="Update project details (Officials only)",
)
async def update_project(
    id: UUID,
    data: ProjectUpdate,
    current_user: ProfileResponse = Depends(require_role(["official"])),
):
    """Update project details.

    Restricted to authorized officials within their assigned department.
    Omitted fields preserve existing values.
    """
    return await project_service.update_project(
        project_id=id,
        official=current_user,
        data=data,
    )


@router.post(
    "/{id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit citizen feedback on a project",
)
async def submit_project_feedback(
    id: UUID,
    data: FeedbackCreate,
    current_user: ProfileResponse = Depends(get_current_user),
):
    """Submit citizen feedback on a published municipal project.

    Derives citizen identity from authentication and verifies project is published.
    """
    return await feedback_service.submit_feedback(
        current_user=current_user,
        project_id=id,
        data=data,
    )


@router.get(
    "/{id}/feedback",
    response_model=List[FeedbackResponse],
    summary="Retrieve feedback for a project (Officials only)",
)
async def list_project_feedback(
    id: UUID,
    category: Optional[str] = Query(None, description="Filter by feedback category"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: ProfileResponse = Depends(require_role(["official"])),
):
    """Retrieve submitted feedback for a specific project.

    Restricted to authorized municipal officials managing the project's department.
    """
    return await feedback_service.list_feedback(
        official=current_user,
        project_id=id,
        category=category,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/{project_id}/feedback/{feedback_id}/convert",
    response_model=ComplaintResponse,
    summary="Convert feedback to a tracked complaint (Officials only)",
)
async def convert_project_feedback(
    project_id: UUID,
    feedback_id: UUID,
    data: Optional[FeedbackConvertRequest] = None,
    current_user: ProfileResponse = Depends(require_role(["official"])),
):
    """Convert actionable project feedback into a tracked municipal complaint.

    Enforces official department boundaries and prevents duplicate conversions.
    """
    return await feedback_service.convert_feedback_to_complaint(
        feedback_id=feedback_id,
        official=current_user,
        data=data,
        expected_project_id=project_id,
    )

