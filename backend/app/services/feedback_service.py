"""Feedback service implementing citizen feedback submission, official retrieval, and feedback-to-complaint conversion."""
import asyncio
from contextlib import asynccontextmanager
import logging
import re
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import HTTPException, status

from app.database.supabase import supabase_service
from app.schemas.complaint import ComplaintResponse
from app.schemas.feedback import FeedbackConvertRequest, FeedbackCreate, FeedbackResponse
from app.schemas.profile import ProfileResponse

logger = logging.getLogger(__name__)

FEEDBACK_REF_REGEX = re.compile(
    r"\[Feedback Ref:\s*([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\s*\]"
)

CANONICAL_FEEDBACK_CATEGORIES = {
    "construction-related inconvenience": "Construction-related inconvenience",
    "inconvenience": "Construction-related inconvenience",
    "road closures or diversions": "Road closures or diversions",
    "road closures": "Road closures or diversions",
    "road closure": "Road closures or diversions",
    "diversions": "Road closures or diversions",
    "diversion": "Road closures or diversions",
    "noise or dust": "Noise or dust",
    "noise": "Noise or dust",
    "dust": "Noise or dust",
    "noise & dust": "Noise or dust",
    "noise and dust": "Noise or dust",
    "damaged nearby infrastructure": "Damaged nearby infrastructure",
    "damaged infrastructure": "Damaged nearby infrastructure",
    "damage": "Damaged nearby infrastructure",
    "accessibility concerns": "Accessibility concerns",
    "accessibility": "Accessibility concerns",
    "other project-related problems": "Other project-related problems",
    "other": "Other project-related problems",
    "general feedback": "Other project-related problems",
    "general": "Other project-related problems",
}

ALL_CANONICAL_NAMES = [
    "Construction-related inconvenience",
    "Road closures or diversions",
    "Noise or dust",
    "Damaged nearby infrastructure",
    "Accessibility concerns",
    "Other project-related problems",
]

DEPARTMENT_ID_TO_CATEGORY: Dict[str, str] = {
    "11111111-1111-1111-1111-111111111111": "Road Infrastructure",
    "22222222-2222-2222-2222-222222222222": "Sanitation",
    "33333333-3333-3333-3333-333333333333": "Electrical",
    "44444444-4444-4444-4444-444444444444": "Water & Sewerage",
    "55555555-5555-5555-5555-555555555555": "Traffic & Transport",
    "66666666-6666-6666-6666-666666666666": "Parks & Public Assets",
}

DEPARTMENT_NAME_TO_CATEGORY: Dict[str, str] = {
    "public works department": "Road Infrastructure",
    "public works": "Road Infrastructure",
    "pwd": "Road Infrastructure",
    "sanitation department": "Sanitation",
    "sanitation": "Sanitation",
    "electrical department": "Electrical",
    "electrical": "Electrical",
    "water & sewerage department": "Water & Sewerage",
    "water and sewerage department": "Water & Sewerage",
    "water department": "Water & Sewerage",
    "sewerage department": "Water & Sewerage",
    "traffic & transport department": "Traffic & Transport",
    "traffic and transport department": "Traffic & Transport",
    "traffic department": "Traffic & Transport",
    "transport department": "Traffic & Transport",
    "parks & public assets department": "Parks & Public Assets",
    "parks and public assets department": "Parks & Public Assets",
    "parks department": "Parks & Public Assets",
}


def normalize_feedback_category(cat: str) -> str:
    """Normalize and validate incoming feedback category string against documented PRD categories."""
    if not cat:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Feedback category cannot be empty. Allowed: {', '.join(ALL_CANONICAL_NAMES)}",
        )
    key = cat.strip().lower()
    if key in CANONICAL_FEEDBACK_CATEGORIES:
        return CANONICAL_FEEDBACK_CATEGORIES[key]

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid feedback category '{cat}'. Allowed categories: {', '.join(ALL_CANONICAL_NAMES)}",
    )


class FeedbackConversionLockManager:
    """In-memory lock manager to serialize concurrent conversions for the same feedback_id.

    IMPORTANT ARCHITECTURAL LIMITATION:
    This lock is a single-process safeguard only. It serializes concurrent conversion requests
    within a single running Python / FastAPI process. It does not provide distributed concurrency
    guarantees across multiple Uvicorn/Gunicorn worker processes or distributed server instances.
    In a multi-process or multi-instance deployment, a database-level unique constraint
    (e.g., public.project_feedback.complaint_id UNIQUE) or distributed lock (e.g., Redis) is required.
    """

    def __init__(self):
        self._locks: Dict[UUID, asyncio.Lock] = {}
        self._ref_counts: Dict[UUID, int] = {}
        self._master_lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire(self, feedback_id: UUID):
        async with self._master_lock:
            if feedback_id not in self._locks:
                self._locks[feedback_id] = asyncio.Lock()
                self._ref_counts[feedback_id] = 0
            self._ref_counts[feedback_id] += 1
            lock = self._locks[feedback_id]

        async with lock:
            try:
                yield
            finally:
                async with self._master_lock:
                    self._ref_counts[feedback_id] -= 1
                    if self._ref_counts[feedback_id] <= 0:
                        self._locks.pop(feedback_id, None)
                        self._ref_counts.pop(feedback_id, None)


class FeedbackService:
    """Service layer for citizen project feedback and conversion workflows."""

    def __init__(self):
        self._lock_manager = FeedbackConversionLockManager()

    async def resolve_complaint_category_for_project(self, project: Dict[str, Any]) -> str:
        """Resolve a schema-valid complaint category based on the project's responsible department.

        Matches seed department UUIDs directly. For non-seed UUIDs, queries the departments table
        and performs fuzzy/keyword matching against municipal department names.
        Raises an explicit HTTP 400 validation error if the department cannot be determined or resolved.
        """
        dept_id_raw = project.get("department_id")
        if not dept_id_raw:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot convert feedback: project does not have an assigned department.",
            )

        dept_id_str = str(dept_id_raw).lower()
        if dept_id_str in DEPARTMENT_ID_TO_CATEGORY:
            return DEPARTMENT_ID_TO_CATEGORY[dept_id_str]

        # Query department record if ID was not in static seed mapping
        try:
            dept_records = await supabase_service.rest_query(
                "departments",
                method="GET",
                params={"id": f"eq.{dept_id_str}", "select": "name"},
            )
            if dept_records and isinstance(dept_records, list) and len(dept_records) > 0:
                dept_name = str(dept_records[0].get("name", "")).strip().lower()
                if dept_name in DEPARTMENT_NAME_TO_CATEGORY:
                    return DEPARTMENT_NAME_TO_CATEGORY[dept_name]
                for key, cat in DEPARTMENT_NAME_TO_CATEGORY.items():
                    if key in dept_name:
                        return cat
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning(f"Failed to query department name for ID {dept_id_str}: {exc}")

        # If department could not be resolved, do NOT silently assign an arbitrary fallback category
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot convert feedback: project department '{dept_id_str}' does not map to a recognized municipal category.",
        )

    async def submit_feedback(
        self,
        current_user: ProfileResponse,
        project_id: UUID,
        data: FeedbackCreate,
    ) -> FeedbackResponse:
        """Submit citizen feedback on a published municipal project."""
        # 1. Citizen identity derived strictly from authenticated user
        citizen_id = current_user.id

        # 2. Validate category and message content
        canonical_category = normalize_feedback_category(data.category)
        clean_message = data.message.strip()
        if len(clean_message) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Feedback message must be at least 3 characters long.",
            )

        # 3. Verify that referenced project exists and is published
        proj_records = await supabase_service.rest_query(
            "projects",
            method="GET",
            params={"id": f"eq.{project_id}", "select": "id,title,department_id,is_published"},
        )
        if not proj_records or not isinstance(proj_records, list) or len(proj_records) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found.",
            )

        project = proj_records[0]
        if not project.get("is_published"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' is not published and cannot accept citizen feedback.",
            )

        # 4. Insert feedback record
        payload = {
            "project_id": str(project_id),
            "citizen_id": str(citizen_id),
            "category": canonical_category,
            "message": clean_message,
        }

        created = await supabase_service.rest_query("project_feedback", method="POST", json_data=payload)
        if not created or not isinstance(created, list) or len(created) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record project feedback in database.",
            )

        rec = created[0]
        rec["project_title"] = project.get("title")
        rec["citizen_name"] = current_user.full_name
        return FeedbackResponse(**rec)

    async def list_feedback(
        self,
        official: ProfileResponse,
        project_id: Optional[UUID] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[FeedbackResponse]:
        """Retrieve submitted project feedback with department boundaries (Officials only)."""
        if official.role != "official":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only authorized municipal officials can view project feedback.",
            )

        params: Dict[str, Any] = {
            "order": "created_at.desc",
            "limit": limit,
            "offset": offset,
            "select": "*",
        }

        # 1. Enforce department boundaries and project filtering
        if project_id:
            # Verify project exists and check department ownership
            proj_records = await supabase_service.rest_query(
                "projects",
                method="GET",
                params={"id": f"eq.{project_id}", "select": "id,title,department_id"},
            )
            if not proj_records or not isinstance(proj_records, list) or len(proj_records) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Project with ID '{project_id}' not found.",
                )
            project = proj_records[0]

            if official.department_id and str(project.get("department_id")) != str(official.department_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You are not authorized to view feedback for projects in another department.",
                )

            params["project_id"] = f"eq.{project_id}"
        else:
            # No specific project requested: department officials can only view feedback for their department's projects
            if official.department_id:
                dept_projects = await supabase_service.rest_query(
                    "projects",
                    method="GET",
                    params={"department_id": f"eq.{official.department_id}", "select": "id,title"},
                )
                if not dept_projects or not isinstance(dept_projects, list) or len(dept_projects) == 0:
                    return []
                project_ids = [str(p["id"]) for p in dept_projects]
                params["project_id"] = f"in.({','.join(project_ids)})"

        # 2. Category filtering
        if category:
            canonical_cat = normalize_feedback_category(category)
            params["category"] = f"eq.{canonical_cat}"

        feedbacks = await supabase_service.rest_query("project_feedback", method="GET", params=params)
        if not feedbacks or not isinstance(feedbacks, list):
            return []

        # 3. Enrich with project titles and safe citizen names
        proj_records = await supabase_service.rest_query("projects", method="GET", params={"select": "id,title"})
        proj_map = {str(p["id"]): p["title"] for p in (proj_records or [])}

        profile_records = await supabase_service.rest_query("profiles", method="GET", params={"select": "id,full_name"})
        name_map = {str(pr["id"]): pr["full_name"] for pr in (profile_records or [])}

        # 4. Resolve feedback-to-complaint relationship using exact description marker: [Feedback Ref: <feedback_id>]
        feedback_ids = [str(fb.get("id")) for fb in feedbacks if fb.get("id")]
        complaint_map: Dict[str, UUID] = {}

        if feedback_ids:
            try:
                # Query complaints in chunks of 25 to prevent URL length limits in PostgREST
                chunk_size = 25
                for i in range(0, len(feedback_ids), chunk_size):
                    chunk = feedback_ids[i:i + chunk_size]
                    or_filters = [f"description.like.*[Feedback Ref: {fid}]*" for fid in chunk]
                    params_complaints = {
                        "or": f"({','.join(or_filters)})",
                        "select": "id,description",
                    }
                    complaint_records = await supabase_service.rest_query(
                        "complaints",
                        method="GET",
                        params=params_complaints,
                    )
                    if complaint_records and isinstance(complaint_records, list):
                        for c_rec in complaint_records:
                            desc = c_rec.get("description") or ""
                            match = FEEDBACK_REF_REGEX.search(desc)
                            if match:
                                ref_id = match.group(1).lower()
                                c_uuid = c_rec.get("id")
                                if c_uuid and ref_id not in complaint_map:
                                    try:
                                        complaint_map[ref_id] = UUID(str(c_uuid))
                                    except (ValueError, TypeError):
                                        pass
            except Exception as exc:
                logger.warning(f"Failed to query complaints for feedback references: {exc}")

        results = []
        for fb in feedbacks:
            fb_id_str = str(fb.get("id", "")).lower()
            p_id = str(fb.get("project_id"))
            c_id = str(fb.get("citizen_id"))
            fb["project_title"] = proj_map.get(p_id, "Infrastructure Project")
            fb["citizen_name"] = name_map.get(c_id, "Citizen")
            fb["complaint_id"] = complaint_map.get(fb_id_str, None)
            results.append(FeedbackResponse(**fb))

        return results

    async def convert_feedback_to_complaint(
        self,
        feedback_id: UUID,
        official: ProfileResponse,
        data: Optional[FeedbackConvertRequest] = None,
        expected_project_id: Optional[UUID] = None,
    ) -> ComplaintResponse:
        """Convert actionable project feedback into a tracked municipal complaint."""
        if official.role != "official":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only authorized officials can convert feedback into a complaint.",
            )

        # 1. Fetch feedback record
        fb_records = await supabase_service.rest_query(
            "project_feedback",
            method="GET",
            params={"id": f"eq.{feedback_id}", "select": "*"},
        )
        if not fb_records or not isinstance(fb_records, list) or len(fb_records) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project feedback with ID '{feedback_id}' not found.",
            )
        feedback = fb_records[0]

        # 2. Validate route project ID matches feedback's associated project ID if supplied
        if expected_project_id and str(feedback.get("project_id")) != str(expected_project_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Route project ID '{expected_project_id}' does not match feedback's associated project ID '{feedback.get('project_id')}'.",
            )

        # 3. Fetch associated project
        proj_records = await supabase_service.rest_query(
            "projects",
            method="GET",
            params={"id": f"eq.{feedback['project_id']}", "select": "*"},
        )
        if not proj_records or not isinstance(proj_records, list) or len(proj_records) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referenced municipal project not found.",
            )
        project = proj_records[0]

        # 4. Department boundary check
        if official.department_id and str(project.get("department_id")) != str(official.department_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You cannot convert feedback for another department's project.",
            )

        # 5. Serialize concurrent conversions for the same feedback ID using in-memory lock
        async with self._lock_manager.acquire(feedback_id):
            # 5a. Duplicate conversion check (inside lock to prevent concurrent races)
            existing_complaints = await supabase_service.rest_query(
                "complaints",
                method="GET",
                params={"description": f"like.*[Feedback Ref: {feedback_id}]*", "select": "id,title,status"},
            )
            if existing_complaints and isinstance(existing_complaints, list) and len(existing_complaints) > 0:
                existing_id = existing_complaints[0].get("id")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"This feedback has already been converted to complaint {existing_id}.",
                )

            # 5b. Resolve schema-valid category dynamically based on project's department
            complaint_category = await self.resolve_complaint_category_for_project(project)
            issue_type = feedback.get("category", "Project Feedback")

            title = (data.title.strip() if (data and data.title) else f"Project Issue: {project.get('title', 'Municipal Project')}")
            priority = (data.priority if data and data.priority else "Medium")
            severity = (data.severity if data and data.severity else 5)

            complaint_payload = {
                "citizen_id": str(feedback["citizen_id"]),
                "title": title,
                "description": f"[Feedback Ref: {feedback_id}] {feedback['message']}",
                "latitude": project.get("latitude", 15.399),
                "longitude": project.get("longitude", 73.812),
                "category": complaint_category,
                "issue_type": issue_type,
                "department_id": str(project["department_id"]),
                "severity": severity,
                "priority": priority,
                "status": "Submitted",
                "report_count": 1,
                "safety_related": False,
            }

            created = await supabase_service.rest_query("complaints", method="POST", json_data=complaint_payload)
            if not created or not isinstance(created, list) or len(created) == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create complaint record from feedback.",
                )

            complaint_record = created[0]
            complaint_id = complaint_record["id"]

            # 5c. Record initial update history entry with compensating rollback on failure
            update_payload = {
                "complaint_id": str(complaint_id),
                "actor_id": str(official.id),
                "status": "Submitted",
                "remarks": f"Complaint created from project feedback {feedback_id} by official {official.full_name}",
            }

            history_success = False
            try:
                hist_res = await supabase_service.rest_query("complaint_updates", method="POST", json_data=update_payload)
                if hist_res is not None and hist_res is not False:
                    history_success = True
            except Exception as exc:
                logger.error(
                    f"Failed to record complaint_updates history for converted complaint {complaint_id}: {exc}",
                    exc_info=True,
                )

            if not history_success:
                logger.warning(
                    f"Initial history insert failed for converted complaint {complaint_id}. Initiating compensating rollback."
                )
                complaint_rolled_back = False
                try:
                    del_res = await supabase_service.rest_query(
                        "complaints",
                        method="DELETE",
                        params={"id": f"eq.{complaint_id}"},
                    )
                    if del_res is not None and del_res is not False:
                        complaint_rolled_back = True
                except Exception as del_exc:
                    logger.error(f"Compensating rollback failed to delete complaint {complaint_id}: {del_exc}", exc_info=True)

                if complaint_rolled_back:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Complaint creation from feedback failed: unable to record initial complaint history. Automatic rollback completed: orphaned complaint record was removed.",
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Complaint creation from feedback failed: unable to record initial complaint history. Attention required: automatic rollback of complaint record could not be completed.",
                    )

            return ComplaintResponse(**complaint_record)


feedback_service = FeedbackService()
