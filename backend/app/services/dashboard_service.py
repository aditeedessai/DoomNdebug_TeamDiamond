"""Dashboard Service implementing business logic, metric aggregations, and pagination.

Task: M4-08 Dashboard APIs (Step 2.1: Service Hardening)
PRD References: Section 7.7 (Dashboard APIs), Section 14 (Dashboard Cards & Views),
               Section 4.8 (Women's Safety Overview)
"""
import logging
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from fastapi import HTTPException, status

from app.database.supabase import supabase_service
from app.schemas.dashboard import (
    CitizenDashboardResponse,
    DepartmentPerformanceStats,
    OfficialDashboardResponse,
    PriorityBreakdownResponse,
    RecentComplaintItem,
    RecentTaskItem,
    SafetyDashboardResponse,
    WorkerDashboardResponse,
)
from app.schemas.profile import ProfileResponse

logger = logging.getLogger(__name__)

# Canonical status groupings based on complaint lifecycle state machine
PENDING_STATUSES = {"Submitted", "Under Review", "Assigned", "Needs More Information"}
IN_PROGRESS_STATUS = "In Progress"
RESOLVED_STATUS = "Resolved"
REJECTED_STATUS = "Rejected"
TERMINAL_STATUSES = {RESOLVED_STATUS, REJECTED_STATUS}

# Inferred dashboard threshold for acute infrastructure hazard identification.
# NOTE: docs/PRD.md and database/schema.sql define physical hazard ratings on an integer scale
# of 1 through 10, but do not specify an official numerical threshold for 'high severity'.
# In Member 3's priority model (backend/app/services/priority_service.py), complaints achieve
# 'High' priority at score 60 (initial severity >= 6) and 'Critical' at score 80 (severity >= 8).
# The threshold of 7 is an inferred dashboard heuristic representing acute physical hazards
# in the top 40% of the rating scale (7 through 10) for safety officer overviews.
# It does not alter or replace Member 3's priority scoring formula.
HIGH_SEVERITY_THRESHOLD = 7


class DashboardService:
    """Service layer managing dashboard analytics and summary metrics."""

    async def _fetch_all_records(
        self,
        table: str,
        base_params: Dict[str, str],
        page_size: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Retrieve all database records across PostgREST pages using sequential pagination.

        Enforces complete dataset retrieval for accurate aggregations:
        - Issues bounded requests of page_size (default 1000).
        - Advances offset sequentially until the final page is reached.
        - Propagates HTTP 503 if any page fails, preventing partial or misleading statistics.
        """
        all_records: List[Dict[str, Any]] = []
        offset = 0

        while True:
            page_params = dict(base_params)
            page_params["limit"] = str(page_size)
            page_params["offset"] = str(offset)
            page_params.setdefault("order", "id.asc")

            batch = await supabase_service.rest_query(table, method="GET", params=page_params)
            if batch is None:
                logger.error(
                    f"Database query failed for table '{table}' at offset {offset} with params: {page_params}"
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database service unavailable. Failed to compute dashboard metrics.",
                )

            if not isinstance(batch, list):
                logger.error(
                    f"Unexpected non-list response from table '{table}' at offset {offset}: {type(batch).__name__}"
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database service unavailable. Failed to compute dashboard metrics.",
                )

            all_records.extend(batch)

            # If fewer than page_size items are returned, we have fetched the final page
            if len(batch) < page_size:
                break

            offset += len(batch)

        return all_records

    async def get_summary(
        self,
        current_user: ProfileResponse,
        department_id: Optional[UUID] = None,
    ) -> Union[CitizenDashboardResponse, OfficialDashboardResponse, WorkerDashboardResponse]:
        """Return role-discriminated dashboard summary cards and recent activity.

        Dispatches based on the authenticated user's role:
        - citizen: personal complaints and public municipal counters.
        - official: department-scoped or city-wide municipal cards.
        - worker: personal task assignments and status counters.
        """
        if current_user.role == "citizen":
            return await self._get_citizen_summary(current_user)
        elif current_user.role == "official":
            return await self._get_official_summary(current_user, department_id=department_id)
        elif current_user.role == "worker":
            return await self._get_worker_summary(current_user)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Dashboard summary is not supported for role '{current_user.role}'.",
            )

    async def _get_citizen_summary(self, citizen: ProfileResponse) -> CitizenDashboardResponse:
        """Calculate personal metrics for an authenticated citizen."""
        citizen_id_str = str(citizen.id)

        # 1. Fetch all citizen complaints for accurate complete aggregation
        c_params = {
            "citizen_id": f"eq.{citizen_id_str}",
            "select": "id,status",
        }
        complaints = await self._fetch_all_records("complaints", c_params)

        my_total = len(complaints)
        my_pending = sum(1 for c in complaints if c.get("status") in PENDING_STATUSES)
        my_in_progress = sum(1 for c in complaints if c.get("status") == IN_PROGRESS_STATUS)
        my_resolved = sum(1 for c in complaints if c.get("status") == RESOLVED_STATUS)
        my_rejected = sum(1 for c in complaints if c.get("status") == REJECTED_STATUS)

        # 2. Fetch recent complaints via a dedicated bounded query (server-side limit 5)
        recent_params = {
            "citizen_id": f"eq.{citizen_id_str}",
            "order": "created_at.desc",
            "limit": "5",
            "select": "id,title,category,status,priority,created_at",
        }
        recent_raw = await supabase_service.rest_query("complaints", method="GET", params=recent_params)
        if recent_raw is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable. Failed to compute dashboard metrics.",
            )
        recent_complaints = [RecentComplaintItem(**c) for c in (recent_raw if isinstance(recent_raw, list) else [])]

        # 3. Count active published projects (Planned or Ongoing)
        p_params = {
            "is_published": "eq.true",
            "status": "in.(Planned,Ongoing)",
            "select": "id",
        }
        projects_raw = await supabase_service.rest_query("projects", method="GET", params=p_params)
        if projects_raw is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable. Failed to compute dashboard metrics.",
            )
        active_projects = len(projects_raw) if isinstance(projects_raw, list) else 0

        # 4. Count active traffic hotspots
        h_params = {"select": "id"}
        hotspots_raw = await supabase_service.rest_query("traffic_hotspots", method="GET", params=h_params)
        if hotspots_raw is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable. Failed to compute dashboard metrics.",
            )
        traffic_hotspots = len(hotspots_raw) if isinstance(hotspots_raw, list) else 0

        return CitizenDashboardResponse(
            my_total=my_total,
            my_pending=my_pending,
            my_in_progress=my_in_progress,
            my_resolved=my_resolved,
            my_rejected=my_rejected,
            active_projects=active_projects,
            traffic_hotspots=traffic_hotspots,
            recent_complaints=recent_complaints,
        )

    async def _get_official_summary(
        self,
        officer: ProfileResponse,
        department_id: Optional[UUID] = None,
    ) -> OfficialDashboardResponse:
        """Calculate municipal summary cards for an authenticated official."""
        # Enforce departmental authorization boundaries
        target_dept_id: Optional[UUID] = None
        if officer.department_id:
            if department_id and department_id != officer.department_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You are not authorized to view dashboard metrics for another department.",
                )
            target_dept_id = officer.department_id
        else:
            target_dept_id = department_id

        # 1. Fetch complaints in authorized scope using complete pagination
        c_params: Dict[str, str] = {
            "select": "id,status,priority,department_id,safety_related",
        }
        if target_dept_id:
            c_params["department_id"] = f"eq.{target_dept_id}"

        # Ordinary officials must NEVER have safety reports included in counts
        if not officer.is_safety_officer:
            c_params["safety_related"] = "eq.false"

        complaints = await self._fetch_all_records("complaints", c_params)

        total_complaints = len(complaints)
        pending_complaints = sum(1 for c in complaints if c.get("status") in PENDING_STATUSES)
        in_progress_complaints = sum(1 for c in complaints if c.get("status") == IN_PROGRESS_STATUS)
        resolved_complaints = sum(1 for c in complaints if c.get("status") == RESOLVED_STATUS)
        high_priority_complaints = sum(1 for c in complaints if c.get("priority") in ("High", "Critical"))
        department_backlog = sum(1 for c in complaints if c.get("status") not in TERMINAL_STATUSES)

        # 2. Fetch recent complaints via a dedicated bounded query (server-side limit 5)
        recent_params: Dict[str, str] = {
            "order": "created_at.desc",
            "limit": "5",
            "select": "id,title,category,status,priority,created_at",
        }
        if target_dept_id:
            recent_params["department_id"] = f"eq.{target_dept_id}"
        if not officer.is_safety_officer:
            recent_params["safety_related"] = "eq.false"

        recent_raw = await supabase_service.rest_query("complaints", method="GET", params=recent_params)
        if recent_raw is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable. Failed to compute dashboard metrics.",
            )
        recent_complaints = [RecentComplaintItem(**c) for c in (recent_raw if isinstance(recent_raw, list) else [])]

        # 3. Count active traffic hotspots
        h_params = {"select": "id"}
        hotspots_raw = await supabase_service.rest_query("traffic_hotspots", method="GET", params=h_params)
        if hotspots_raw is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable. Failed to compute dashboard metrics.",
            )
        traffic_hotspots = len(hotspots_raw) if isinstance(hotspots_raw, list) else 0

        return OfficialDashboardResponse(
            total_complaints=total_complaints,
            pending_complaints=pending_complaints,
            in_progress_complaints=in_progress_complaints,
            resolved_complaints=resolved_complaints,
            high_priority_complaints=high_priority_complaints,
            department_backlog=department_backlog,
            traffic_hotspots=traffic_hotspots,
            recent_complaints=recent_complaints,
        )

    async def _get_worker_summary(self, worker_user: ProfileResponse) -> WorkerDashboardResponse:
        """Calculate task assignment metrics for an authenticated field worker."""
        # 1. Resolve worker record using workers.profile_id = current_user.id
        w_params = {
            "profile_id": f"eq.{worker_user.id}",
            "select": "id",
        }
        worker_records = await supabase_service.rest_query("workers", method="GET", params=w_params)
        if worker_records is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable. Failed to compute dashboard metrics.",
            )

        if not worker_records or not isinstance(worker_records, list) or len(worker_records) == 0:
            # Worker profile row is not yet registered in workers table
            return WorkerDashboardResponse()

        worker_id = worker_records[0]["id"]

        # 2. Fetch all assignments for this worker using complete pagination
        a_params = {
            "worker_id": f"eq.{worker_id}",
            "select": "id,status",
        }
        assignments = await self._fetch_all_records("assignments", a_params)

        total_assigned_tasks = len(assignments)
        pending_tasks = sum(1 for a in assignments if a.get("status") == "Assigned")
        in_progress_tasks = sum(1 for a in assignments if a.get("status") == "In Progress")
        completed_tasks = sum(1 for a in assignments if a.get("status") == "Completed")

        # 3. Fetch recent tasks via a dedicated bounded query (server-side limit 5)
        recent_a_params = {
            "worker_id": f"eq.{worker_id}",
            "order": "created_at.desc",
            "limit": "5",
            "select": "id,task_description,status,created_at",
        }
        recent_tasks_raw = await supabase_service.rest_query("assignments", method="GET", params=recent_a_params)
        if recent_tasks_raw is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable. Failed to compute dashboard metrics.",
            )
        recent_tasks = [RecentTaskItem(**a) for a in (recent_tasks_raw if isinstance(recent_tasks_raw, list) else [])]

        return WorkerDashboardResponse(
            total_assigned_tasks=total_assigned_tasks,
            pending_tasks=pending_tasks,
            in_progress_tasks=in_progress_tasks,
            completed_tasks=completed_tasks,
            recent_tasks=recent_tasks,
        )

    async def get_department_stats(
        self,
        officer: ProfileResponse,
        department_id: Optional[UUID] = None,
    ) -> List[DepartmentPerformanceStats]:
        """Calculate department breakdown, complaint counts, and resolution rate."""
        if officer.role != "official":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Department statistics are restricted to officials (role: '{officer.role}').",
            )

        # Enforce departmental authorization boundaries
        target_dept_id: Optional[UUID] = None
        if officer.department_id:
            if department_id and department_id != officer.department_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You are not authorized to view statistics for another department.",
                )
            target_dept_id = officer.department_id
        else:
            target_dept_id = department_id

        # 1. Fetch departments
        d_params: Dict[str, str] = {"order": "name.asc", "select": "id,name"}
        if target_dept_id:
            d_params["id"] = f"eq.{target_dept_id}"

        dept_records = await supabase_service.rest_query("departments", method="GET", params=d_params)
        if dept_records is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable. Failed to compute dashboard metrics.",
            )
        departments = dept_records if isinstance(dept_records, list) else []

        # 2. Fetch complaints in authorized scope using complete pagination
        c_params: Dict[str, str] = {"select": "id,department_id,status,safety_related"}
        if target_dept_id:
            c_params["department_id"] = f"eq.{target_dept_id}"

        # Ordinary officials must NEVER have safety reports included in department stats
        if not officer.is_safety_officer:
            c_params["safety_related"] = "eq.false"

        complaints = await self._fetch_all_records("complaints", c_params)

        # 3. Aggregate metrics per department
        results: List[DepartmentPerformanceStats] = []
        for dept in departments:
            dept_id_str = str(dept["id"])
            dept_complaints = [c for c in complaints if str(c.get("department_id")) == dept_id_str]

            tot = len(dept_complaints)
            pend = sum(1 for c in dept_complaints if c.get("status") in PENDING_STATUSES)
            inp = sum(1 for c in dept_complaints if c.get("status") == IN_PROGRESS_STATUS)
            res = sum(1 for c in dept_complaints if c.get("status") == RESOLVED_STATUS)
            rate = round((res / tot) * 100.0, 1) if tot > 0 else 0.0

            results.append(
                DepartmentPerformanceStats(
                    department_id=UUID(dept_id_str),
                    department_name=dept.get("name", "Department"),
                    total_complaints=tot,
                    pending_complaints=pend,
                    in_progress_complaints=inp,
                    resolved_complaints=res,
                    resolution_rate=rate,
                )
            )

        return results

    async def get_priority_breakdown(
        self,
        officer: ProfileResponse,
        department_id: Optional[UUID] = None,
    ) -> PriorityBreakdownResponse:
        """Calculate priority distribution across Critical, High, Medium, and Low."""
        if officer.role != "official":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Priority breakdown is restricted to officials (role: '{officer.role}').",
            )

        # Enforce departmental authorization boundaries
        target_dept_id: Optional[UUID] = None
        if officer.department_id:
            if department_id and department_id != officer.department_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You are not authorized to view statistics for another department.",
                )
            target_dept_id = officer.department_id
        else:
            target_dept_id = department_id

        # 1. Fetch complaints in authorized scope using complete pagination
        c_params: Dict[str, str] = {"select": "id,priority,department_id,safety_related"}
        if target_dept_id:
            c_params["department_id"] = f"eq.{target_dept_id}"

        # Ordinary officials must NEVER have safety reports included in priority breakdown
        if not officer.is_safety_officer:
            c_params["safety_related"] = "eq.false"

        complaints = await self._fetch_all_records("complaints", c_params)

        crit = sum(1 for c in complaints if c.get("priority") == "Critical")
        high = sum(1 for c in complaints if c.get("priority") == "High")
        med = sum(1 for c in complaints if c.get("priority") == "Medium")
        low = sum(1 for c in complaints if c.get("priority") == "Low")
        total = crit + high + med + low

        return PriorityBreakdownResponse(
            critical=crit,
            high=high,
            medium=med,
            low=low,
            total=total,
        )

    async def get_safety_summary(self, officer: ProfileResponse) -> SafetyDashboardResponse:
        """Calculate aggregated safety incident statistics for designated safety officers."""
        if not officer.is_safety_officer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Restricted to designated safety officers only.",
            )

        s_params: Dict[str, str] = {
            "safety_related": "eq.true",
            "select": "id,safety_category,status,severity,department_id",
        }
        if officer.department_id:
            s_params["department_id"] = f"eq.{officer.department_id}"

        records = await self._fetch_all_records("complaints", s_params)

        total_safety_reports = len(records)
        pending_investigations = sum(1 for r in records if r.get("status") in PENDING_STATUSES)
        in_progress_investigations = sum(1 for r in records if r.get("status") == IN_PROGRESS_STATUS)
        resolved_investigations = sum(1 for r in records if r.get("status") == RESOLVED_STATUS)
        high_severity_count = sum(
            1 for r in records if (r.get("severity") or 0) >= HIGH_SEVERITY_THRESHOLD
        )

        category_breakdown: Dict[str, int] = {}
        for r in records:
            cat = r.get("safety_category") or "Unspecified Safety Concern"
            category_breakdown[cat] = category_breakdown.get(cat, 0) + 1

        return SafetyDashboardResponse(
            total_safety_reports=total_safety_reports,
            pending_investigations=pending_investigations,
            in_progress_investigations=in_progress_investigations,
            resolved_investigations=resolved_investigations,
            high_severity_count=high_severity_count,
            category_breakdown=category_breakdown,
        )


# Global singleton instance
dashboard_service = DashboardService()
