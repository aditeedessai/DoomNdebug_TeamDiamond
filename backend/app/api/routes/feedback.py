"""API route endpoints for feedback collection, listing, and complaint conversion."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user, require_role
from app.schemas.complaint import ComplaintResponse
from app.schemas.feedback import FeedbackConvertRequest, FeedbackCreate, FeedbackResponse
from app.schemas.profile import ProfileResponse
from app.services.feedback_service import feedback_service

router = APIRouter()


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit citizen feedback (Compatible with citizenService.js)",
)
async def submit_feedback_root(
    data: FeedbackCreate,
    current_user: ProfileResponse = Depends(get_current_user),
):
    """Submit citizen feedback on a project.

    Accepts project_id in request body for compatibility with frontend citizenService.
    """
    if not data.project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Field 'project_id' is required when submitting feedback to /api/v1/feedback.",
        )

    return await feedback_service.submit_feedback(
        current_user=current_user,
        project_id=data.project_id,
        data=data,
    )


@router.get(
    "",
    response_model=List[FeedbackResponse],
    summary="Retrieve all project feedback (Officials only)",
)
async def list_all_feedback(
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    category: Optional[str] = Query(None, description="Filter by feedback category"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: ProfileResponse = Depends(require_role(["official"])),
):
    """Retrieve submitted project feedback.

    Restricted to authorized officials. Department officials can only view feedback
    for projects belonging to their assigned department.
    """
    return await feedback_service.list_feedback(
        official=current_user,
        project_id=project_id,
        category=category,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/{id}/convert-to-complaint",
    response_model=ComplaintResponse,
    summary="Convert feedback to a tracked complaint (Officials only)",
)
async def convert_feedback_to_complaint_root(
    id: UUID,
    data: Optional[FeedbackConvertRequest] = None,
    current_user: ProfileResponse = Depends(require_role(["official"])),
):
    """Convert actionable project feedback into a tracked municipal complaint.

    Enforces department boundary permissions and prevents duplicate complaint creation.
    """
    return await feedback_service.convert_feedback_to_complaint(
        feedback_id=id,
        official=current_user,
        data=data,
    )

