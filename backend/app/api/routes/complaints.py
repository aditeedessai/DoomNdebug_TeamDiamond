"""Complaint API routes for creation, listing, detail, updates, and photograph uploads."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.api.deps import get_current_user, require_role
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintDetailResponse,
    ComplaintResponse,
    ComplaintUpdate,
    ImageUploadResponse,
    OfficialStatusUpdate,
)
from app.schemas.profile import ProfileResponse
from app.services.complaint_service import complaint_service
from app.services.storage_service import storage_service

router = APIRouter()


@router.post(
    "",
    response_model=ComplaintResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new civic complaint",
)
async def create_complaint(
    complaint_data: ComplaintCreate,
    current_user: ProfileResponse = Depends(get_current_user),
):
    """Citizen creates a new civic complaint.

    Citizen ID is automatically derived from the authenticated profile.
    Initial status is set to 'Submitted' and initial update history is recorded.
    """
    return await complaint_service.create_complaint(
        citizen=current_user,
        data=complaint_data,
    )


@router.get(
    "/my",
    response_model=List[ComplaintResponse],
    summary="List complaints submitted by authenticated citizen",
)
async def get_my_complaints(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by complaint status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: ProfileResponse = Depends(get_current_user),
):
    """Retrieve all complaints submitted by the calling citizen, ordered newest first."""
    return await complaint_service.get_my_complaints(
        citizen=current_user,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/upload-image",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a photograph for a complaint",
)
async def upload_complaint_image(
    file: UploadFile = File(...),
    current_user: ProfileResponse = Depends(get_current_user),
):
    """Upload a JPEG, PNG, or WebP photograph (max 5 MB).

    File is verified via magic bytes, securely namespaced under the user's ID
    in the private 'complaint-images' bucket, and returns an image path for the complaint record.
    """
    upload_result = await storage_service.upload_complaint_image(
        file=file,
        user_id=str(current_user.id),
    )
    return ImageUploadResponse(**upload_result)


@router.get(
    "",
    response_model=List[ComplaintResponse],
    summary="List all complaints (Officials only)",
)
async def list_complaints_for_officials(
    department_id: Optional[UUID] = Query(None, description="Filter by municipal department"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by lifecycle status"),
    priority: Optional[str] = Query(None, description="Filter by priority level"),
    safety_related: Optional[bool] = Query(None, description="Filter safety reports (Safety Officers only)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: ProfileResponse = Depends(require_role(["official"])),
):
    """List complaints for officials.

    Safety-related complaints are strictly hidden unless the official is a designated safety officer.
    Workers are denied access to this register.
    """
    return await complaint_service.list_complaints_for_official(
        official=current_user,
        department_id=department_id,
        status_filter=status_filter,
        priority=priority,
        safety_related=safety_related,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{id}",
    response_model=ComplaintDetailResponse,
    summary="Retrieve single complaint detail and timeline",
)
async def get_complaint_detail(
    id: UUID,
    current_user: ProfileResponse = Depends(get_current_user),
):
    """Retrieve detailed complaint record and timeline.

    Enforces ownership for citizens, department authorization for officials,
    and assigned task validation for workers.
    """
    return await complaint_service.get_complaint_by_id(
        complaint_id=id,
        current_user=current_user,
    )


@router.patch(
    "/{id}",
    response_model=ComplaintResponse,
    summary="Update complaint details (Citizen owner only)",
)
async def update_complaint(
    id: UUID,
    data: ComplaintUpdate,
    current_user: ProfileResponse = Depends(get_current_user),
):
    """Citizen updates an editable complaint.

    Only permitted if status is 'Submitted' or 'Needs More Information'.
    """
    return await complaint_service.update_complaint_as_citizen(
        complaint_id=id,
        citizen=current_user,
        data=data,
    )


@router.patch(
    "/{id}/status",
    response_model=ComplaintResponse,
    summary="Update complaint status, department, and priority (Officials only)",
)
async def update_complaint_status(
    id: UUID,
    data: OfficialStatusUpdate,
    current_user: ProfileResponse = Depends(require_role(["official"])),
):
    """Official updates complaint status and assignment.

    Appends an entry to the status history with required official remarks.
    """
    return await complaint_service.update_status_as_official(
        complaint_id=id,
        official=current_user,
        data=data,
    )

