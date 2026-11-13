"""Complaint service implementing business logic, ownership checks, and status history."""
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import HTTPException, status

from app.database.supabase import supabase_service
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintDetailResponse,
    ComplaintResponse,
    ComplaintUpdate,
    ComplaintUpdateItem,
    OfficialStatusUpdate,
)
from app.schemas.profile import ProfileResponse
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)


class ComplaintService:
    """Service layer for complaint management and history tracking."""

    async def create_complaint(
        self,
        citizen: ProfileResponse,
        data: ComplaintCreate,
    ) -> ComplaintResponse:
        """Create a new citizen complaint and record initial history update."""
        citizen_id_str = str(citizen.id)

        # 1. Enforce image ownership if image was provided
        if data.image_url:
            if not storage_service.validate_image_ownership(data.image_url, citizen_id_str):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unauthorized: You cannot link an image uploaded by another user.",
                )

        # 2. Build payload (derived fields strictly protected from user input)
        payload = {
            "citizen_id": citizen_id_str,
            "title": data.title.strip(),
            "description": data.description.strip(),
            "latitude": data.latitude,
            "longitude": data.longitude,
            "category": data.category.strip(),
            "issue_type": data.issue_type.strip(),
            "image_url": data.image_url,
            "safety_related": data.safety_related,
            "safety_category": data.safety_category,
            "status": "Submitted",
            "priority": "Medium",
            "severity": 5,
            "report_count": 1,
        }

        # 3. Persist to database
        created = await supabase_service.rest_query("complaints", method="POST", json_data=payload)

        if not created or not isinstance(created, list) or len(created) == 0:
            # Clean up uploaded image if database insert failed
            if data.image_url:
                await storage_service.delete_complaint_image(data.image_url)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record complaint in database. Image upload was rolled back.",
            )

        complaint_record = created[0]
        complaint_id = complaint_record["id"]

        # 4. Create initial status update history entry with compensating rollback on failure
        update_payload = {
            "complaint_id": complaint_id,
            "actor_id": citizen_id_str,
            "status": "Submitted",
            "remarks": "Complaint submitted by citizen",
        }

        history_success = False
        original_exc: Optional[Exception] = None
        try:
            update_result = await supabase_service.rest_query(
                "complaint_updates", method="POST", json_data=update_payload
            )
            if update_result is not None and update_result is not False:
                history_success = True
        except Exception as exc:
            original_exc = exc
            logger.error(
                f"Failed to record complaint_updates history for complaint {complaint_id}: {exc}",
                exc_info=True,
            )

        if not history_success:
            logger.warning(
                f"Initial history insert failed for complaint {complaint_id}. Initiating compensating rollback."
            )
            rollback_errors = []
            complaint_rolled_back = False
            image_cleaned_up = True if not data.image_url else False

            # Rollback 1: Delete newly created complaint by its exact UUID
            try:
                delete_resp = await supabase_service.rest_query(
                    "complaints",
                    method="DELETE",
                    params={"id": f"eq.{complaint_id}"},
                )
                if delete_resp is not None and delete_resp is not False:
                    complaint_rolled_back = True
                else:
                    rollback_errors.append(f"Database failed to delete orphaned complaint {complaint_id}")
            except Exception as del_exc:
                logger.error(f"Rollback error deleting complaint {complaint_id}: {del_exc}", exc_info=True)
                rollback_errors.append(f"Failed to delete orphaned complaint: {del_exc}")

            # Rollback 2: Delete uploaded image from storage if an image was attached
            if data.image_url:
                try:
                    img_deleted = await storage_service.delete_complaint_image(data.image_url)
                    if img_deleted:
                        image_cleaned_up = True
                    else:
                        rollback_errors.append(f"Storage failed to delete uploaded image '{data.image_url}'")
                except Exception as img_exc:
                    logger.error(f"Image cleanup error for '{data.image_url}': {img_exc}", exc_info=True)
                    rollback_errors.append(f"Failed to clean up image: {img_exc}")

            # Report client-facing status without leaking raw database exceptions or internal infrastructure details
            detail_parts = [
                "Complaint creation failed: unable to record initial complaint history.",
            ]
            if complaint_rolled_back and image_cleaned_up:
                detail_parts.append("Automatic rollback completed: complaint record and attached files were removed.")
            else:
                attention_items = []
                if not complaint_rolled_back:
                    attention_items.append("complaint record could not be removed")
                if not image_cleaned_up:
                    attention_items.append("attached photograph could not be removed")
                detail_parts.append(
                    f"Rollback requires administrative attention: {', '.join(attention_items)}."
                )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=" ".join(detail_parts),
            )

        # 5. Generate signed URL for response if image is attached
        if complaint_record.get("image_url"):
            complaint_record["image_signed_url"] = await storage_service.create_signed_url(
                complaint_record["image_url"]
            )

        return ComplaintResponse(**complaint_record)

    async def get_my_complaints(
        self,
        citizen: ProfileResponse,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ComplaintResponse]:
        """Retrieve complaints submitted by the authenticated citizen."""
        params = {
            "citizen_id": f"eq.{citizen.id}",
            "order": "created_at.desc",
            "limit": str(limit),
            "offset": str(offset),
            "select": "*",
        }
        if status_filter:
            params["status"] = f"eq.{status_filter}"

        records = await supabase_service.rest_query("complaints", method="GET", params=params)
        if not records or not isinstance(records, list):
            return []

        results = []
        for r in records:
            if r.get("image_url"):
                r["image_signed_url"] = await storage_service.create_signed_url(r["image_url"])
            results.append(ComplaintResponse(**r))

        return results

    async def get_complaint_by_id(
        self,
        complaint_id: UUID,
        current_user: ProfileResponse,
    ) -> ComplaintDetailResponse:
        """Fetch a specific complaint and verify role/ownership permissions."""
        params = {"id": f"eq.{complaint_id}", "select": "*"}
        records = await supabase_service.rest_query("complaints", method="GET", params=params)

        if not records or not isinstance(records, list) or len(records) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complaint with ID '{complaint_id}' was not found.",
            )

        complaint = records[0]

        # 1. Citizen authorization: can only view own complaint
        if current_user.role == "citizen":
            if str(complaint["citizen_id"]) != str(current_user.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You do not own this complaint record.",
                )

        # 2. Official authorization
        elif current_user.role == "official":
            # Safety officer check
            if complaint.get("safety_related") and not current_user.is_safety_officer:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Restricted safety report requiring designated safety officer authorization.",
                )

        # 3. Worker authorization: must be assigned to this complaint
        elif current_user.role == "worker":
            # Check assignments table
            assignment_params = {
                "complaint_id": f"eq.{complaint_id}",
                "select": "id,worker_id,workers!inner(profile_id)",
                "workers.profile_id": f"eq.{current_user.id}",
            }
            assignments = await supabase_service.rest_query("assignments", method="GET", params=assignment_params)
            if not assignments or not isinstance(assignments, list) or len(assignments) == 0:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You are not assigned to work on this complaint.",
                )

        # Fetch update history timeline
        update_params = {
            "complaint_id": f"eq.{complaint_id}",
            "order": "created_at.asc",
            "select": "*",
        }
        updates_raw = await supabase_service.rest_query("complaint_updates", method="GET", params=update_params)
        updates = [ComplaintUpdateItem(**u) for u in updates_raw] if isinstance(updates_raw, list) else []

        # Generate signed URL for image
        if complaint.get("image_url"):
            complaint["image_signed_url"] = await storage_service.create_signed_url(complaint["image_url"])

        return ComplaintDetailResponse(
            **complaint,
            updates=updates,
        )

    async def update_complaint_as_citizen(
        self,
        complaint_id: UUID,
        citizen: ProfileResponse,
        data: ComplaintUpdate,
    ) -> ComplaintResponse:
        """Citizen updates an existing complaint.

        Only allowed while status is 'Submitted' or 'Needs More Information'.
        """
        # Fetch current record
        detail = await self.get_complaint_by_id(complaint_id, citizen)

        # Verify allowed status
        if detail.status not in ("Submitted", "Needs More Information"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot edit complaint: Current status '{detail.status}' cannot be modified by citizen.",
            )

        # Enforce image ownership if image is being updated
        if data.image_url and data.image_url != detail.image_url:
            if not storage_service.validate_image_ownership(data.image_url, str(citizen.id)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unauthorized: You cannot link an image uploaded by another user.",
                )

        # Build update dict with only non-None values
        update_fields = data.model_dump(exclude_unset=True)
        if not update_fields:
            return detail

        params = {"id": f"eq.{complaint_id}"}
        updated = await supabase_service.rest_query(
            "complaints",
            method="PATCH",
            params=params,
            json_data=update_fields,
        )

        if not updated or not isinstance(updated, list) or len(updated) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update complaint record.",
            )

        rec = updated[0]
        if rec.get("image_url"):
            rec["image_signed_url"] = await storage_service.create_signed_url(rec["image_url"])

        return ComplaintResponse(**rec)

    async def update_status_as_official(
        self,
        complaint_id: UUID,
        official: ProfileResponse,
        data: OfficialStatusUpdate,
    ) -> ComplaintResponse:
        """Update complaint lifecycle status, department, and priority as an official."""
        # Fetch current record to verify official permissions
        detail = await self.get_complaint_by_id(complaint_id, official)

        # Safety officer check
        if detail.safety_related and not official.is_safety_officer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only designated safety officers may update safety-related complaints.",
            )

        # Department boundary check
        if official.department_id and detail.department_id:
            if official.department_id != detail.department_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You are not authorized to update complaints outside your assigned department.",
                )

        # Build update fields
        update_fields: Dict[str, Any] = {"status": data.status}
        if data.department_id:
            update_fields["department_id"] = str(data.department_id)
        if data.priority:
            update_fields["priority"] = data.priority
        if data.severity is not None:
            update_fields["severity"] = data.severity

        params = {"id": f"eq.{complaint_id}"}
        updated = await supabase_service.rest_query(
            "complaints",
            method="PATCH",
            params=params,
            json_data=update_fields,
        )

        if not updated or not isinstance(updated, list) or len(updated) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update complaint status in database.",
            )

        # Record history update in complaint_updates
        history_payload = {
            "complaint_id": str(complaint_id),
            "actor_id": str(official.id),
            "status": data.status,
            "remarks": data.remarks.strip(),
        }
        await supabase_service.rest_query("complaint_updates", method="POST", json_data=history_payload)

        rec = updated[0]
        if rec.get("image_url"):
            rec["image_signed_url"] = await storage_service.create_signed_url(rec["image_url"])

        return ComplaintResponse(**rec)

    async def list_complaints_for_official(
        self,
        official: ProfileResponse,
        department_id: Optional[UUID] = None,
        status_filter: Optional[str] = None,
        priority: Optional[str] = None,
        safety_related: Optional[bool] = None,
        include_unassigned: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ComplaintResponse]:
        """List complaints for officials with department boundaries and safety restrictions."""
        # Workers are prohibited from accessing the general official complaint listing
        if official.role == "worker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Workers do not have access to the general complaint register. View assigned tasks instead.",
            )

        params: Dict[str, str] = {
            "order": "created_at.desc",
            "limit": str(limit),
            "offset": str(offset),
            "select": "*",
        }

        # Safety restriction: Non-safety officers can NEVER see safety-related reports
        if not official.is_safety_officer:
            params["safety_related"] = "eq.false"
        elif safety_related is not None:
            params["safety_related"] = f"eq.{str(safety_related).lower()}"

        # Department filter & unassigned triage
        effective_dept = department_id or official.department_id
        if effective_dept:
            if include_unassigned:
                # Department official with include_unassigned=True:
                # Return complaints assigned to their department OR unassigned complaints (department_id IS NULL)
                params["or"] = f"(department_id.eq.{effective_dept},department_id.is.null)"
            else:
                # Department official default:
                # Return complaints strictly assigned to their department
                params["department_id"] = f"eq.{effective_dept}"
        # If effective_dept is None (General official with department_id=NULL and no query department_id),
        # no department constraint is added, preserving existing general triage behaviour.

        if status_filter:
            params["status"] = f"eq.{status_filter}"

        if priority:
            params["priority"] = f"eq.{priority}"

        records = await supabase_service.rest_query("complaints", method="GET", params=params)
        if not records or not isinstance(records, list):
            return []

        results = []
        for r in records:
            if r.get("image_url"):
                r["image_signed_url"] = await storage_service.create_signed_url(r["image_url"])
            results.append(ComplaintResponse(**r))

        return results


# Global complaint service instance
complaint_service = ComplaintService()

