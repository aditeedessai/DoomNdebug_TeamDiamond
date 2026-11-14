"""Assignment Service managing municipal field workers, crews, and task assignments.

Task: M4-09 Worker and Officer Assignments (Step 3: Service Layer)
PRD References: Section 4.7 (Field Worker Assignment), Section 6.7 (workers),
               Section 6.8 (assignments), Section 7.6 (Workers and assignments APIs)
Database References: database/schema.sql (workers, assignments, chk_assignment_target, complaint_updates)
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID
from fastapi import HTTPException, status

from app.database.supabase import supabase_service
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentDetailResponse,
    AssignmentResponse,
    AssignmentStatus,
    AssignmentUpdate,
    WorkerAvailability,
    WorkerResponse,
)
from app.schemas.profile import ProfileResponse

logger = logging.getLogger(__name__)

# Canonical complaint statuses where task assignments are permitted
ASSIGNABLE_COMPLAINT_STATUSES = {"Submitted", "Under Review", "Assigned", "Needs More Information"}
TERMINAL_COMPLAINT_STATUSES = {"Resolved", "Rejected"}


class AssignmentService:
    """Service layer managing field workers, teams, and task assignments."""

    async def _fetch_all_records(
        self,
        table: str,
        base_params: Dict[str, str],
        page_size: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Retrieve all database records across PostgREST pages using sequential pagination."""
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
                    detail="Database service unavailable.",
                )

            if not isinstance(batch, list):
                logger.error(
                    f"Unexpected non-list response from table '{table}' at offset {offset}: {type(batch).__name__}"
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database service unavailable.",
                )

            all_records.extend(batch)

            if len(batch) < page_size:
                break

            offset += len(batch)

        return all_records

    async def _get_worker_for_user(self, user: ProfileResponse) -> Optional[Dict[str, Any]]:
        """Resolve the worker database record associated with an authenticated profile."""
        params = {"profile_id": f"eq.{user.id}", "select": "*"}
        records = await supabase_service.rest_query("workers", method="GET", params=params)
        if records is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable.",
            )
        if isinstance(records, list) and len(records) > 0:
            return records[0]
        return None

    # =========================================================================
    # A. WORKER MANAGEMENT
    # =========================================================================

    async def list_workers(
        self,
        user: ProfileResponse,
        department_id: Optional[UUID] = None,
        availability: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[WorkerResponse]:
        """List municipal field workers within authorized scope.

        - Officials view field workers in their authorized department scope.
        - General officials (no department) can view municipal-wide workers or filter.
        - Workers can only view their own worker profile, never a full directory.
        - Citizens are strictly denied access (HTTP 403).
        """
        if user.role == "citizen":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Citizens cannot access worker directory.",
            )

        # Worker role: restricted strictly to own profile
        if user.role == "worker":
            worker_row = await self._get_worker_for_user(user)
            if not worker_row:
                return []
            dept_name = None
            if worker_row.get("department_id"):
                d_rec = await supabase_service.rest_query(
                    "departments",
                    method="GET",
                    params={"id": f"eq.{worker_row['department_id']}", "select": "name"},
                )
                if isinstance(d_rec, list) and len(d_rec) > 0:
                    dept_name = d_rec[0].get("name")
            return [
                WorkerResponse(
                    id=UUID(worker_row["id"]),
                    profile_id=UUID(worker_row["profile_id"]) if worker_row.get("profile_id") else None,
                    name=worker_row["name"],
                    department_id=UUID(worker_row["department_id"]),
                    department_name=dept_name,
                    availability=worker_row.get("availability", "Available"),
                    phone=worker_row.get("phone"),
                    created_at=datetime.fromisoformat(worker_row["created_at"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(worker_row["updated_at"].replace("Z", "+00:00")),
                )
            ]

        # Official role: enforce department boundaries
        target_dept_id: Optional[UUID] = None
        if user.department_id:
            if department_id and department_id != user.department_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You are not authorized to view workers outside your assigned department.",
                )
            target_dept_id = user.department_id
        else:
            target_dept_id = department_id

        params: Dict[str, str] = {
            "order": "name.asc,id.asc",
            "limit": str(limit),
            "offset": str(offset),
            "select": "id,profile_id,name,department_id,availability,phone,created_at,updated_at",
        }
        if target_dept_id:
            params["department_id"] = f"eq.{target_dept_id}"
        if availability:
            params["availability"] = f"eq.{availability}"

        workers_raw = await supabase_service.rest_query("workers", method="GET", params=params)
        if workers_raw is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable.",
            )

        workers = workers_raw if isinstance(workers_raw, list) else []
        if not workers:
            return []

        # Resolve department names in batch
        dept_ids = {w["department_id"] for w in workers if w.get("department_id")}
        dept_map: Dict[str, str] = {}
        if dept_ids:
            d_params = {"id": f"in.({','.join(dept_ids)})", "select": "id,name"}
            d_records = await supabase_service.rest_query("departments", method="GET", params=d_params)
            if isinstance(d_records, list):
                dept_map = {d["id"]: d["name"] for d in d_records}

        results: List[WorkerResponse] = []
        for w in workers:
            results.append(
                WorkerResponse(
                    id=UUID(w["id"]),
                    profile_id=UUID(w["profile_id"]) if w.get("profile_id") else None,
                    name=w["name"],
                    department_id=UUID(w["department_id"]),
                    department_name=dept_map.get(w["department_id"]),
                    availability=w.get("availability", "Available"),
                    phone=w.get("phone"),
                    created_at=datetime.fromisoformat(w["created_at"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(w["updated_at"].replace("Z", "+00:00")),
                )
            )
        return results

    async def get_worker_by_id(
        self,
        user: ProfileResponse,
        worker_id: UUID,
    ) -> WorkerResponse:
        """Retrieve a specific worker profile by ID enforcing role and department scope."""
        if user.role == "citizen":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Citizens cannot access worker profiles.",
            )

        params = {
            "id": f"eq.{worker_id}",
            "select": "id,profile_id,name,department_id,availability,phone,created_at,updated_at",
        }
        records = await supabase_service.rest_query("workers", method="GET", params=params)
        if records is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable.",
            )
        if not records or not isinstance(records, list) or len(records) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Worker with ID '{worker_id}' was not found.",
            )

        worker = records[0]

        # Worker role: can view only own worker record
        if user.role == "worker":
            if not worker.get("profile_id") or str(worker["profile_id"]) != str(user.id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Worker with ID '{worker_id}' was not found.",
                )

        # Official role: enforce department boundary
        if user.role == "official" and user.department_id:
            if str(worker.get("department_id")) != str(user.department_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Worker with ID '{worker_id}' was not found in your department.",
                )

        dept_name = None
        if worker.get("department_id"):
            d_records = await supabase_service.rest_query(
                "departments",
                method="GET",
                params={"id": f"eq.{worker['department_id']}", "select": "name"},
            )
            if isinstance(d_records, list) and len(d_records) > 0:
                dept_name = d_records[0].get("name")

        return WorkerResponse(
            id=UUID(worker["id"]),
            profile_id=UUID(worker["profile_id"]) if worker.get("profile_id") else None,
            name=worker["name"],
            department_id=UUID(worker["department_id"]),
            department_name=dept_name,
            availability=worker.get("availability", "Available"),
            phone=worker.get("phone"),
            created_at=datetime.fromisoformat(worker["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(worker["updated_at"].replace("Z", "+00:00")),
        )

    # =========================================================================
    # B. CREATE ASSIGNMENTS
    # =========================================================================

    async def create_assignment(
        self,
        official: ProfileResponse,
        data: AssignmentCreate,
    ) -> AssignmentResponse:
        """Create a task assignment for a complaint or traffic hotspot.

        Enforces:
        - Officials only; officer_id derived from authenticated profile.
        - Single target rule: exactly one of complaint_id or hotspot_id.
        - Target existence, department scoping, and safety report segregation.
        - Complaint lifecycle update to 'Assigned' and complaint_updates history logging.
        - Hotspot assignment isolation (no complaint updates written).
        """
        if official.role != "official":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only authorized officials can create assignments.",
            )

        # 1. Validate target exclusivity (defense-in-depth matching schema constraint)
        has_c = data.complaint_id is not None
        has_h = data.hotspot_id is not None
        if (has_c and has_h) or (not has_c and not has_h):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exactly one assignment target must be provided: complaint_id or hotspot_id.",
            )

        # 2. Validate worker existence and availability
        w_records = await supabase_service.rest_query(
            "workers",
            method="GET",
            params={"id": f"eq.{data.worker_id}", "select": "*"},
        )
        if w_records is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable.",
            )
        if not w_records or not isinstance(w_records, list) or len(w_records) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Worker with ID '{data.worker_id}' was not found.",
            )
        worker = w_records[0]

        if worker.get("availability") == "Unavailable":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Worker '{worker.get('name')}' is currently Unavailable and cannot accept assignments.",
            )

        complaint: Optional[Dict[str, Any]] = None
        hotspot: Optional[Dict[str, Any]] = None

        # 3. Handle Complaint Target
        if data.complaint_id:
            c_records = await supabase_service.rest_query(
                "complaints",
                method="GET",
                params={"id": f"eq.{data.complaint_id}", "select": "*"},
            )
            if c_records is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database service unavailable.",
                )
            if not c_records or not isinstance(c_records, list) or len(c_records) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Complaint with ID '{data.complaint_id}' was not found.",
                )
            complaint = c_records[0]

            # Safety restriction: Ordinary officials CANNOT assign safety reports
            if complaint.get("safety_related") and not official.is_safety_officer:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Ordinary officials cannot access or assign safety-related complaints.",
                )

            # Department boundary check
            if official.department_id:
                if complaint.get("department_id") and str(complaint["department_id"]) != str(official.department_id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: You cannot assign complaints outside your department.",
                    )
                if str(worker.get("department_id")) != str(official.department_id):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Worker department does not match your authorized department.",
                    )
            elif complaint.get("department_id"):
                # Municipal-wide official: verify worker department matches complaint department
                if str(worker.get("department_id")) != str(complaint["department_id"]):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Worker department does not match complaint department.",
                    )

            # Complaint lifecycle check
            current_st = complaint.get("status", "Submitted")
            if current_st in TERMINAL_COMPLAINT_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot assign tasks to a complaint in terminal status '{current_st}'.",
                )

        # 4. Handle Traffic Hotspot Target
        elif data.hotspot_id:
            h_records = await supabase_service.rest_query(
                "traffic_hotspots",
                method="GET",
                params={"id": f"eq.{data.hotspot_id}", "select": "*"},
            )
            if h_records is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database service unavailable.",
                )
            if not h_records or not isinstance(h_records, list) or len(h_records) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Traffic hotspot with ID '{data.hotspot_id}' was not found.",
                )
            hotspot = h_records[0]

        # 5. Insert into assignments table
        assignment_payload = {
            "complaint_id": str(data.complaint_id) if data.complaint_id else None,
            "hotspot_id": str(data.hotspot_id) if data.hotspot_id else None,
            "worker_id": str(data.worker_id),
            "officer_id": str(official.id),
            "task_description": data.task_description.strip(),
            "status": data.status or "Assigned",
        }

        created_res = await supabase_service.rest_query(
            "assignments",
            method="POST",
            json_data=assignment_payload,
        )
        if created_res is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable. Failed to create assignment record.",
            )

        created_row: Dict[str, Any] = {}
        if isinstance(created_res, list) and len(created_res) > 0:
            created_row = created_res[0]
        else:
            # Re-fetch created record if representation header did not return body
            lookup = await supabase_service.rest_query(
                "assignments",
                method="GET",
                params={
                    "worker_id": f"eq.{data.worker_id}",
                    "officer_id": f"eq.{official.id}",
                    "order": "created_at.desc",
                    "limit": "1",
                },
            )
            if isinstance(lookup, list) and len(lookup) > 0:
                created_row = lookup[0]

        assignment_id_str = str(created_row.get("id"))

        # 6. Synchronize Complaint Lifecycle & Timeline History (Compensating rollback on failure)
        if data.complaint_id and complaint:
            try:
                # If currently Submitted or Under Review, advance complaint status to Assigned
                current_st = complaint.get("status", "Submitted")
                if current_st in ("Submitted", "Under Review"):
                    comp_patch = {"status": "Assigned", "updated_at": datetime.now(timezone.utc).isoformat()}
                    c_update = await supabase_service.rest_query(
                        "complaints",
                        method="PATCH",
                        params={"id": f"eq.{data.complaint_id}"},
                        json_data=comp_patch,
                    )
                    if c_update is None:
                        logger.error(f"Failed to advance complaint {data.complaint_id} status to Assigned")

                # Insert timeline history entry
                history_payload = {
                    "complaint_id": str(data.complaint_id),
                    "actor_id": str(official.id),
                    "status": "Assigned",
                    "remarks": f"Task assigned to field crew '{worker.get('name')}': {data.task_description.strip()}",
                }
                h_insert = await supabase_service.rest_query(
                    "complaint_updates",
                    method="POST",
                    json_data=history_payload,
                )
                if h_insert is None:
                    logger.error(f"Failed to record complaint update history for complaint {data.complaint_id}")

            except Exception as sync_exc:
                logger.error(f"Error synchronizing complaint status: {sync_exc}. Executing compensating rollback.")
                # Compensating rollback: delete created assignment to prevent orphaned/inconsistent assignment
                if assignment_id_str:
                    await supabase_service.rest_query(
                        "assignments",
                        method="DELETE",
                        params={"id": f"eq.{assignment_id_str}"},
                    )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Failed to synchronize complaint status and history. Assignment creation rolled back.",
                )

        return AssignmentResponse(
            id=UUID(created_row["id"]),
            complaint_id=UUID(created_row["complaint_id"]) if created_row.get("complaint_id") else None,
            hotspot_id=UUID(created_row["hotspot_id"]) if created_row.get("hotspot_id") else None,
            worker_id=UUID(created_row["worker_id"]) if created_row.get("worker_id") else None,
            worker_name=worker.get("name"),
            officer_id=UUID(created_row["officer_id"]),
            officer_name=official.full_name,
            task_description=created_row.get("task_description", data.task_description),
            status=created_row.get("status", data.status or "Assigned"),
            created_at=datetime.fromisoformat(created_row["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(created_row["updated_at"].replace("Z", "+00:00")),
        )

    # =========================================================================
    # C. LIST ASSIGNMENTS
    # =========================================================================

    async def list_assignments(
        self,
        user: ProfileResponse,
        status_filter: Optional[str] = None,
        complaint_id: Optional[UUID] = None,
        hotspot_id: Optional[UUID] = None,
        worker_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AssignmentResponse]:
        """List assignments enforcing strict role, department, and privacy scoping.

        - Workers view ONLY their own task assignments.
        - Officials view assignments within their authorized department scope.
        - Ordinary officials NEVER see assignments linked to safety reports.
        - Citizens receive HTTP 403.
        """
        if user.role == "citizen":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Citizens cannot access assignment registers.",
            )

        params: Dict[str, str] = {
            "order": "created_at.desc,id.asc",
            "limit": str(limit),
            "offset": str(offset),
            "select": "id,complaint_id,hotspot_id,worker_id,officer_id,task_description,status,created_at,updated_at",
        }

        # 1. Worker Role Scoping
        if user.role == "worker":
            worker_row = await self._get_worker_for_user(user)
            if not worker_row:
                return []
            params["worker_id"] = f"eq.{worker_row['id']}"

        # 2. Official Role Scoping
        elif user.role == "official":
            if user.department_id:
                if department_id and department_id != user.department_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: You are not authorized to view assignments outside your department.",
                    )
            if worker_id:
                params["worker_id"] = f"eq.{worker_id}"

        if status_filter:
            params["status"] = f"eq.{status_filter}"
        if complaint_id:
            params["complaint_id"] = f"eq.{complaint_id}"
        if hotspot_id:
            params["hotspot_id"] = f"eq.{hotspot_id}"

        raw_assignments = await supabase_service.rest_query("assignments", method="GET", params=params)
        if raw_assignments is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable.",
            )

        assignments = raw_assignments if isinstance(raw_assignments, list) else []
        if not assignments:
            return []

        # 3. Privacy & Department Boundary Enforcement for Officials
        if user.role == "official":
            target_dept_id = user.department_id or department_id
            complaint_ids = [a["complaint_id"] for a in assignments if a.get("complaint_id")]
            complaint_map: Dict[str, Dict[str, Any]] = {}
            if complaint_ids:
                c_params = {
                    "id": f"in.({','.join(complaint_ids)})",
                    "select": "id,department_id,safety_related",
                }
                c_recs = await supabase_service.rest_query("complaints", method="GET", params=c_params)
                if isinstance(c_recs, list):
                    complaint_map = {c["id"]: c for c in c_recs}

            worker_ids_all = [a["worker_id"] for a in assignments if a.get("worker_id")]
            worker_dept_map: Dict[str, str] = {}
            if worker_ids_all:
                w_params = {
                    "id": f"in.({','.join(worker_ids_all)})",
                    "select": "id,department_id",
                }
                w_recs = await supabase_service.rest_query("workers", method="GET", params=w_params)
                if isinstance(w_recs, list):
                    worker_dept_map = {w["id"]: w.get("department_id") for w in w_recs}

            filtered_assignments: List[Dict[str, Any]] = []
            for a in assignments:
                cid = a.get("complaint_id")
                wid = a.get("worker_id")

                # Ordinary officials: strictly exclude safety-related reports
                if cid and cid in complaint_map:
                    comp = complaint_map[cid]
                    if comp.get("safety_related") and not user.is_safety_officer:
                        continue

                # Department-scoped officials: assignment must belong to authorized department
                if target_dept_id:
                    target_dept_str = str(target_dept_id)
                    matches_comp = cid and cid in complaint_map and str(complaint_map[cid].get("department_id")) == target_dept_str
                    matches_worker = wid and wid in worker_dept_map and str(worker_dept_map[wid]) == target_dept_str
                    if not matches_comp and not matches_worker:
                        continue

                filtered_assignments.append(a)
            assignments = filtered_assignments

        if not assignments:
            return []

        # 4. Resolve worker names and officer names in batch
        unique_w_ids = {a["worker_id"] for a in assignments if a.get("worker_id")}
        unique_o_ids = {a["officer_id"] for a in assignments if a.get("officer_id")}

        worker_names: Dict[str, str] = {}
        if unique_w_ids:
            w_res = await supabase_service.rest_query(
                "workers",
                method="GET",
                params={"id": f"in.({','.join(unique_w_ids)})", "select": "id,name"},
            )
            if isinstance(w_res, list):
                worker_names = {w["id"]: w["name"] for w in w_res}

        officer_names: Dict[str, str] = {}
        if unique_o_ids:
            o_res = await supabase_service.rest_query(
                "profiles",
                method="GET",
                params={"id": f"in.({','.join(unique_o_ids)})", "select": "id,full_name"},
            )
            if isinstance(o_res, list):
                officer_names = {o["id"]: o["full_name"] for o in o_res}

        results: List[AssignmentResponse] = []
        for a in assignments:
            results.append(
                AssignmentResponse(
                    id=UUID(a["id"]),
                    complaint_id=UUID(a["complaint_id"]) if a.get("complaint_id") else None,
                    hotspot_id=UUID(a["hotspot_id"]) if a.get("hotspot_id") else None,
                    worker_id=UUID(a["worker_id"]) if a.get("worker_id") else None,
                    worker_name=worker_names.get(a.get("worker_id")),
                    officer_id=UUID(a["officer_id"]),
                    officer_name=officer_names.get(a.get("officer_id")),
                    task_description=a.get("task_description", ""),
                    status=a.get("status", "Assigned"),
                    created_at=datetime.fromisoformat(a["created_at"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(a["updated_at"].replace("Z", "+00:00")),
                )
            )
        return results

    # =========================================================================
    # D. GET ASSIGNMENT DETAILS
    # =========================================================================

    async def get_assignment_by_id(
        self,
        user: ProfileResponse,
        assignment_id: UUID,
    ) -> AssignmentDetailResponse:
        """Retrieve assignment detail metadata enforcing strict role and safety authorization."""
        if user.role == "citizen":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Citizens cannot access assignment details.",
            )

        params = {"id": f"eq.{assignment_id}", "select": "*"}
        records = await supabase_service.rest_query("assignments", method="GET", params=params)
        if records is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable.",
            )
        if not records or not isinstance(records, list) or len(records) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assignment with ID '{assignment_id}' was not found.",
            )

        assignment = records[0]

        # 1. Worker Authorization: must match assigned worker profile
        if user.role == "worker":
            worker_row = await self._get_worker_for_user(user)
            if not worker_row or str(assignment.get("worker_id")) != str(worker_row["id"]):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Assignment with ID '{assignment_id}' was not found.",
                )

        # 2. Target Resolution & Official Authorization
        complaint: Optional[Dict[str, Any]] = None
        hotspot: Optional[Dict[str, Any]] = None

        if assignment.get("complaint_id"):
            c_records = await supabase_service.rest_query(
                "complaints",
                method="GET",
                params={"id": f"eq.{assignment['complaint_id']}", "select": "*"},
            )
            if isinstance(c_records, list) and len(c_records) > 0:
                complaint = c_records[0]

        elif assignment.get("hotspot_id"):
            h_records = await supabase_service.rest_query(
                "traffic_hotspots",
                method="GET",
                params={"id": f"eq.{assignment['hotspot_id']}", "select": "*"},
            )
            if isinstance(h_records, list) and len(h_records) > 0:
                hotspot = h_records[0]

        # Official scope checks
        if user.role == "official":
            if complaint and complaint.get("safety_related") and not user.is_safety_officer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Assignment with ID '{assignment_id}' was not found.",
                )
            if user.department_id:
                dept_str = str(user.department_id)
                comp_match = complaint and str(complaint.get("department_id")) == dept_str
                # Check worker department if complaint unassigned to department
                worker_match = False
                if assignment.get("worker_id"):
                    w_rec = await supabase_service.rest_query(
                        "workers",
                        method="GET",
                        params={"id": f"eq.{assignment['worker_id']}", "select": "department_id"},
                    )
                    if isinstance(w_rec, list) and len(w_rec) > 0:
                        worker_match = str(w_rec[0].get("department_id")) == dept_str
                if not comp_match and not worker_match:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Assignment with ID '{assignment_id}' was not found in your department.",
                    )

        # Resolve worker name and officer name
        worker_name = None
        if assignment.get("worker_id"):
            w_res = await supabase_service.rest_query(
                "workers",
                method="GET",
                params={"id": f"eq.{assignment['worker_id']}", "select": "name"},
            )
            if isinstance(w_res, list) and len(w_res) > 0:
                worker_name = w_res[0].get("name")

        officer_name = None
        if assignment.get("officer_id"):
            o_res = await supabase_service.rest_query(
                "profiles",
                method="GET",
                params={"id": f"eq.{assignment['officer_id']}", "select": "full_name"},
            )
            if isinstance(o_res, list) and len(o_res) > 0:
                officer_name = o_res[0].get("full_name")

        target_type = "complaint" if assignment.get("complaint_id") else "hotspot"

        return AssignmentDetailResponse(
            id=UUID(assignment["id"]),
            complaint_id=UUID(assignment["complaint_id"]) if assignment.get("complaint_id") else None,
            hotspot_id=UUID(assignment["hotspot_id"]) if assignment.get("hotspot_id") else None,
            worker_id=UUID(assignment["worker_id"]) if assignment.get("worker_id") else None,
            worker_name=worker_name,
            officer_id=UUID(assignment["officer_id"]),
            officer_name=officer_name,
            task_description=assignment.get("task_description", ""),
            status=assignment.get("status", "Assigned"),
            created_at=datetime.fromisoformat(assignment["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(assignment["updated_at"].replace("Z", "+00:00")),
            target_type=target_type,
            complaint_title=complaint.get("title") if complaint else None,
            complaint_category=complaint.get("category") if complaint else None,
            complaint_priority=complaint.get("priority") if complaint else None,
            hotspot_congestion=hotspot.get("congestion_level") if hotspot else None,
            hotspot_description=hotspot.get("description") if hotspot else None,
        )

    # =========================================================================
    # E. UPDATE ASSIGNMENTS
    # =========================================================================

    async def update_assignment(
        self,
        user: ProfileResponse,
        assignment_id: UUID,
        data: AssignmentUpdate,
    ) -> AssignmentResponse:
        """Update assignment status, task instructions, or worker reassignment.

        - Workers can update only their own assignment, updating status and notes.
        - Workers cannot reassign worker_id or change task descriptions.
        - Officials can update status, description, or reassign workers.
        - Completed assignments cannot be reopened (terminal status).
        - Invalid status transitions are rejected (HTTP 400).
        - Status transitions synchronize complaint lifecycle and insert timeline history.
        """
        if user.role == "citizen":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Citizens cannot modify assignments.",
            )

        # 1. Retrieve existing assignment record
        records = await supabase_service.rest_query(
            "assignments",
            method="GET",
            params={"id": f"eq.{assignment_id}", "select": "*"},
        )
        if records is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable.",
            )
        if not records or not isinstance(records, list) or len(records) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assignment with ID '{assignment_id}' was not found.",
            )
        current = records[0]
        current_st = current.get("status", "Assigned")

        # 2. Worker Role Restrictions
        if user.role == "worker":
            worker_row = await self._get_worker_for_user(user)
            if not worker_row or str(current.get("worker_id")) != str(worker_row["id"]):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Assignment with ID '{assignment_id}' was not found.",
                )
            if data.worker_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Workers are not authorized to reassign workers.",
                )
            if data.task_description is not None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Workers are not authorized to modify task descriptions.",
                )

        # 3. Official Role Restrictions & Safety Segregation
        complaint: Optional[Dict[str, Any]] = None
        if current.get("complaint_id"):
            c_records = await supabase_service.rest_query(
                "complaints",
                method="GET",
                params={"id": f"eq.{current['complaint_id']}", "select": "*"},
            )
            if isinstance(c_records, list) and len(c_records) > 0:
                complaint = c_records[0]

        if user.role == "official":
            if complaint and complaint.get("safety_related") and not user.is_safety_officer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Assignment with ID '{assignment_id}' was not found.",
                )
            if user.department_id:
                dept_str = str(user.department_id)
                comp_dept = str(complaint.get("department_id")) if complaint else None
                if comp_dept and comp_dept != dept_str:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: You cannot modify assignments outside your department.",
                    )

        # 4. Reassignment Validation (Officials only)
        new_worker: Optional[Dict[str, Any]] = None
        if data.worker_id and str(data.worker_id) != str(current.get("worker_id")):
            w_rec = await supabase_service.rest_query(
                "workers",
                method="GET",
                params={"id": f"eq.{data.worker_id}", "select": "*"},
            )
            if w_rec is None:
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service unavailable.")
            if not w_rec or not isinstance(w_rec, list) or len(w_rec) == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Worker with ID '{data.worker_id}' was not found.")
            new_worker = w_rec[0]

            if user.role == "official" and user.department_id:
                if str(new_worker.get("department_id")) != str(user.department_id):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Reassigned worker must belong to your authorized department.",
                    )

        # 5. Assignment Status Lifecycle Transition Rules
        new_status = data.status or current_st
        if current_st == "Completed":
            if data.status and data.status != "Completed":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Completed assignments are terminal and cannot be reopened.",
                )
        elif current_st == "In Progress":
            if data.status == "Assigned":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid status transition: Cannot revert 'In Progress' assignment back to 'Assigned'.",
                )

        # 6. Apply Database Update
        patch_payload: Dict[str, Any] = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if data.status:
            patch_payload["status"] = data.status
        if data.task_description:
            patch_payload["task_description"] = data.task_description.strip()
        if data.worker_id:
            patch_payload["worker_id"] = str(data.worker_id)

        update_res = await supabase_service.rest_query(
            "assignments",
            method="PATCH",
            params={"id": f"eq.{assignment_id}"},
            json_data=patch_payload,
        )
        if update_res is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable. Failed to update assignment.",
            )

        # 7. Synchronize Complaint Lifecycle & History (For complaint-linked assignments)
        if current.get("complaint_id") and complaint:
            cid = current["complaint_id"]
            comp_st = complaint.get("status", "Submitted")

            # Transition: Assigned -> In Progress
            if current_st == "Assigned" and new_status == "In Progress":
                if comp_st == "Assigned":
                    await supabase_service.rest_query(
                        "complaints",
                        method="PATCH",
                        params={"id": f"eq.{cid}"},
                        json_data={"status": "In Progress", "updated_at": datetime.now(timezone.utc).isoformat()},
                    )
                remarks_text = data.notes.strip() if data.notes else f"Field work commenced: {current.get('task_description')}"
                await supabase_service.rest_query(
                    "complaint_updates",
                    method="POST",
                    json_data={
                        "complaint_id": str(cid),
                        "actor_id": str(user.id),
                        "status": "In Progress",
                        "remarks": remarks_text,
                    },
                )

            # Transition: In Progress -> Completed
            elif new_status == "Completed" and current_st != "Completed":
                remarks_text = data.notes.strip() if data.notes else "Field task marked completed by worker."
                await supabase_service.rest_query(
                    "complaint_updates",
                    method="POST",
                    json_data={
                        "complaint_id": str(cid),
                        "actor_id": str(user.id),
                        "status": comp_st if comp_st in ("In Progress", "Assigned") else "In Progress",
                        "remarks": remarks_text,
                    },
                )

            # Reassignment event
            elif new_worker and str(new_worker["id"]) != str(current.get("worker_id")):
                reassign_remark = data.notes.strip() if data.notes else f"Task reassigned to '{new_worker['name']}'"
                await supabase_service.rest_query(
                    "complaint_updates",
                    method="POST",
                    json_data={
                        "complaint_id": str(cid),
                        "actor_id": str(user.id),
                        "status": comp_st,
                        "remarks": reassign_remark,
                    },
                )

        # Re-fetch updated assignment
        updated_records = await supabase_service.rest_query(
            "assignments",
            method="GET",
            params={"id": f"eq.{assignment_id}", "select": "*"},
        )
        if not updated_records or not isinstance(updated_records, list):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable.",
            )
        updated = updated_records[0]

        # Resolve names
        w_name = None
        if updated.get("worker_id"):
            w_res = await supabase_service.rest_query(
                "workers",
                method="GET",
                params={"id": f"eq.{updated['worker_id']}", "select": "name"},
            )
            if isinstance(w_res, list) and len(w_res) > 0:
                w_name = w_res[0].get("name")

        o_name = None
        if updated.get("officer_id"):
            o_res = await supabase_service.rest_query(
                "profiles",
                method="GET",
                params={"id": f"eq.{updated['officer_id']}", "select": "full_name"},
            )
            if isinstance(o_res, list) and len(o_res) > 0:
                o_name = o_res[0].get("full_name")

        return AssignmentResponse(
            id=UUID(updated["id"]),
            complaint_id=UUID(updated["complaint_id"]) if updated.get("complaint_id") else None,
            hotspot_id=UUID(updated["hotspot_id"]) if updated.get("hotspot_id") else None,
            worker_id=UUID(updated["worker_id"]) if updated.get("worker_id") else None,
            worker_name=w_name,
            officer_id=UUID(updated["officer_id"]),
            officer_name=o_name,
            task_description=updated.get("task_description", ""),
            status=updated.get("status", "Assigned"),
            created_at=datetime.fromisoformat(updated["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(updated["updated_at"].replace("Z", "+00:00")),
        )


# Global singleton instance
assignment_service = AssignmentService()

