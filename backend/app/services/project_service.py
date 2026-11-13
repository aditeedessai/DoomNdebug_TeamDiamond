"""Project service implementing municipal project CRUD, visibility checks, and department boundaries."""
from datetime import date, datetime
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import HTTPException, status

from app.database.supabase import supabase_service
from app.schemas.profile import ProfileResponse
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

logger = logging.getLogger(__name__)

VALID_PROJECT_STATUSES = {"Planned", "Ongoing", "Completed"}


class ProjectService:
    """Service layer for municipal infrastructure projects."""

    async def validate_department_exists(self, department_id: UUID) -> str:
        """Verify that the referenced municipal department exists and return its name."""
        dept_records = await supabase_service.rest_query(
            "departments",
            method="GET",
            params={"id": f"eq.{department_id}", "select": "id,name"},
        )
        if not dept_records or not isinstance(dept_records, list) or len(dept_records) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Target department with ID '{department_id}' does not exist.",
            )
        return dept_records[0].get("name", "Department")

    async def get_project_raw(self, project_id: UUID) -> Dict[str, Any]:
        """Fetch raw project record by ID without authorization checks."""
        records = await supabase_service.rest_query(
            "projects",
            method="GET",
            params={"id": f"eq.{project_id}", "select": "*"},
        )
        if not records or not isinstance(records, list) or len(records) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found.",
            )
        return records[0]

    async def list_projects(
        self,
        current_user: Optional[ProfileResponse] = None,
        department_id: Optional[UUID] = None,
        status_filter: Optional[str] = None,
        is_published: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ProjectResponse]:
        """List municipal projects with role-aware visibility and department filtering."""
        params: Dict[str, Any] = {
            "order": "created_at.desc",
            "limit": limit,
            "offset": offset,
            "select": "*",
        }

        # 1. Enforce publication visibility
        # Citizens, workers, or unauthenticated callers ONLY see published projects
        if not current_user or current_user.role != "official":
            params["is_published"] = "eq.true"
        else:
            # Official visibility
            if is_published is not None:
                params["is_published"] = f"eq.{str(is_published).lower()}"
            elif current_user.department_id:
                # Department officials see published projects OR unpublished projects in their own department
                params["or"] = f"(is_published.eq.true,department_id.eq.{current_user.department_id})"
            # General officials (department_id is None) see all projects by default

        # 2. Filter by department if requested
        if department_id:
            params["department_id"] = f"eq.{department_id}"

        # 3. Filter by status if requested
        if status_filter:
            if status_filter not in VALID_PROJECT_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid project status '{status_filter}'. Allowed statuses: {', '.join(sorted(VALID_PROJECT_STATUSES))}",
                )
            params["status"] = f"eq.{status_filter}"

        records = await supabase_service.rest_query("projects", method="GET", params=params)
        if not records or not isinstance(records, list):
            return []

        # Enrich department names
        dept_records = await supabase_service.rest_query("departments", method="GET", params={"select": "id,name"})
        dept_map = {}
        if dept_records and isinstance(dept_records, list):
            for d in dept_records:
                dept_map[str(d["id"])] = d["name"]

        results = []
        for rec in records:
            dept_id_str = str(rec.get("department_id"))
            rec["department_name"] = dept_map.get(dept_id_str, "Municipal Department")
            results.append(ProjectResponse(**rec))

        return results

    async def get_project_by_id(
        self,
        project_id: UUID,
        current_user: Optional[ProfileResponse] = None,
    ) -> ProjectResponse:
        """Retrieve individual project details with publication and department access checks."""
        rec = await self.get_project_raw(project_id)

        # Enforce visibility rules
        if not current_user or current_user.role != "official":
            if not rec.get("is_published"):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Project with ID '{project_id}' not found or is unpublished.",
                )
        else:
            # Official access
            if not rec.get("is_published"):
                # Unpublished draft project
                if current_user.department_id and str(rec.get("department_id")) != str(current_user.department_id):
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Project with ID '{project_id}' not found or inaccessible for your department.",
                    )

        # Enrich department name
        dept_records = await supabase_service.rest_query(
            "departments",
            method="GET",
            params={"id": f"eq.{rec['department_id']}", "select": "name"},
        )
        if dept_records and isinstance(dept_records, list) and len(dept_records) > 0:
            rec["department_name"] = dept_records[0].get("name")
        else:
            rec["department_name"] = "Municipal Department"

        return ProjectResponse(**rec)

    async def create_project(
        self,
        official: ProfileResponse,
        data: ProjectCreate,
    ) -> ProjectResponse:
        """Create a new municipal project (Officials only)."""
        if official.role != "official":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only authorized officials can create projects.",
            )

        # Validate target department exists
        dept_name = await self.validate_department_exists(data.department_id)

        # Department boundary check
        if official.department_id and str(data.department_id) != str(official.department_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Department officials cannot create projects for another department.",
            )

        # Validate dates
        if data.expected_end_date < data.start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="expected_end_date cannot be earlier than start_date.",
            )

        # Validate status
        if data.status and data.status not in VALID_PROJECT_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{data.status}'. Allowed: {', '.join(sorted(VALID_PROJECT_STATUSES))}",
            )

        payload = {
            "title": data.title.strip(),
            "description": data.description.strip(),
            "department_id": str(data.department_id),
            "latitude": data.latitude,
            "longitude": data.longitude,
            "start_date": str(data.start_date),
            "expected_end_date": str(data.expected_end_date),
            "status": data.status or "Planned",
            "is_published": bool(data.is_published),
        }

        created = await supabase_service.rest_query("projects", method="POST", json_data=payload)
        if not created or not isinstance(created, list) or len(created) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record project in database.",
            )

        rec = created[0]
        rec["department_name"] = dept_name
        return ProjectResponse(**rec)

    async def update_project(
        self,
        project_id: UUID,
        official: ProfileResponse,
        data: ProjectUpdate,
    ) -> ProjectResponse:
        """Update existing municipal project details (Officials only)."""
        if official.role != "official":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only authorized officials can update projects.",
            )

        existing = await self.get_project_raw(project_id)

        # Department boundary check
        if official.department_id:
            if str(existing.get("department_id")) != str(official.department_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You are not authorized to update projects outside your assigned department.",
                )
            if data.department_id and str(data.department_id) != str(official.department_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Department officials cannot transfer projects across departments.",
                )

        # If general official changes department_id, validate target department exists
        dept_name = None
        if data.department_id:
            dept_name = await self.validate_department_exists(data.department_id)

        # Validate status if supplied
        if data.status and data.status not in VALID_PROJECT_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{data.status}'. Allowed: {', '.join(sorted(VALID_PROJECT_STATUSES))}",
            )

        # Validate dates consistency
        def _parse_date(d: Any) -> date:
            if isinstance(d, date):
                return d
            return datetime.strptime(str(d), "%Y-%m-%d").date()

        current_start = _parse_date(existing["start_date"])
        current_end = _parse_date(existing["expected_end_date"])
        effective_start = data.start_date or current_start
        effective_end = data.expected_end_date or current_end

        if effective_end < effective_start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="expected_end_date cannot be earlier than start_date.",
            )

        # Build PATCH payload (preserve existing values when omitted)
        update_payload: Dict[str, Any] = {}
        if data.title is not None:
            update_payload["title"] = data.title.strip()
        if data.description is not None:
            update_payload["description"] = data.description.strip()
        if data.department_id is not None:
            update_payload["department_id"] = str(data.department_id)
        if data.latitude is not None:
            update_payload["latitude"] = data.latitude
        if data.longitude is not None:
            update_payload["longitude"] = data.longitude
        if data.start_date is not None:
            update_payload["start_date"] = str(data.start_date)
        if data.expected_end_date is not None:
            update_payload["expected_end_date"] = str(data.expected_end_date)
        if data.status is not None:
            update_payload["status"] = data.status
        if data.is_published is not None:
            update_payload["is_published"] = data.is_published

        if not update_payload:
            # No changes requested, return current state
            return await self.get_project_by_id(project_id, official)

        updated = await supabase_service.rest_query(
            "projects",
            method="PATCH",
            params={"id": f"eq.{project_id}"},
            json_data=update_payload,
        )
        if not updated or not isinstance(updated, list) or len(updated) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update project record in database.",
            )

        rec = updated[0]
        if not dept_name:
            dept_records = await supabase_service.rest_query(
                "departments",
                method="GET",
                params={"id": f"eq.{rec['department_id']}", "select": "name"},
            )
            if dept_records and isinstance(dept_records, list) and len(dept_records) > 0:
                dept_name = dept_records[0].get("name")
        rec["department_name"] = dept_name or "Municipal Department"

        return ProjectResponse(**rec)


project_service = ProjectService()

