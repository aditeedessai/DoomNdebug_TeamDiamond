"""Safety Service implementing business logic for safety reports and investigations.

Task: M4-07 Safety Report Handling
PRD References: Section 4.8 (Women's Safety & Unsafe Locations), Section 7.5 (Safety Reporting)
"""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import HTTPException, status

from app.database.supabase import supabase_service
from app.schemas.ai import AIAnalysisRequest
from app.schemas.complaint import ComplaintUpdateItem
from app.schemas.profile import ProfileResponse
from app.schemas.safety import (
    SafetyInvestigationUpdate,
    SafetyReportCreate,
    SafetyReportDetailResponse,
    SafetyReportResponse,
)
from app.services.ai_service import ai_service
from app.services.complaint_service import ALLOWED_TRANSITIONS, VALID_STATUSES
from app.services.priority_service import priority_service
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)


class SafetyService:
    """Service layer managing public and women's infrastructure safety reports."""

    async def create_safety_report(
        self,
        citizen: ProfileResponse,
        data: SafetyReportCreate,
    ) -> SafetyReportResponse:
        """Citizen submits a new safety infrastructure report.

        Derives citizen_id from authenticated profile, enforces image ownership,
        runs AI triage, forces safety_related=True, and inserts initial history
        entry with compensating rollback on failure.
        """
        citizen_id_str = str(citizen.id)

        # 1. Enforce image ownership if image was provided
        if data.image_url:
            if not storage_service.validate_image_ownership(data.image_url, citizen_id_str):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unauthorized: You cannot link an image uploaded by another user.",
                )

        # 2. Invoke Member 3 AI analysis with deterministic fallback
        ai_request = AIAnalysisRequest(
            description=data.description.strip(),
            latitude=data.latitude,
            longitude=data.longitude,
            image_url=data.image_url,
        )
        try:
            ai_result = await ai_service.analyze_complaint(ai_request)
        except Exception as ai_exc:
            logger.warning(
                f"AI analysis failed for safety report: {ai_exc}. Using deterministic fallback."
            )
            ai_result = ai_service.get_fallback_response(
                ai_request,
                reason="AI analysis service unavailable. Queued for manual triage.",
            )

        # 3. Calculate deterministic priority using Member 3 priority service
        calculated_priority = priority_service.calculate_priority(
            severity=ai_result.severity,
            report_count=1,
            overdue_bonus=0,
        )

        # 4. Resolve AI department against departments table
        resolved_dept_id: Optional[str] = None
        resolved_dept_name: Optional[str] = None
        if ai_result.department:
            try:
                dept_records = await supabase_service.rest_query(
                    "departments",
                    method="GET",
                    params={"name": f"eq.{ai_result.department}", "select": "id,name"},
                )
                if dept_records and isinstance(dept_records, list) and len(dept_records) > 0:
                    resolved_dept_id = str(dept_records[0]["id"])
                    resolved_dept_name = dept_records[0].get("name")
            except Exception as d_exc:
                logger.warning(f"Failed to query department ID for '{ai_result.department}': {d_exc}")

        # 5. Build title, category, and issue type
        final_title = data.title.strip() if data.title else (
            ai_result.suggested_title or f"Safety Concern: {data.safety_category}"
        )
        final_category = (
            ai_result.category
            if (ai_result.category and ai_result.category != "Other")
            else "Unsafe public infrastructure"
        )
        final_issue_type = (
            data.safety_category
            if data.safety_category
            else (ai_result.issue_type if ai_result.issue_type else "Safety Concern")
        )

        # 6. Build database payload (safety_related is unconditionally forced to True)
        payload = {
            "citizen_id": citizen_id_str,
            "title": final_title,
            "description": data.description.strip(),
            "latitude": data.latitude,
            "longitude": data.longitude,
            "category": final_category,
            "issue_type": final_issue_type,
            "department_id": resolved_dept_id,
            "image_url": data.image_url,
            "safety_related": True,
            "safety_category": data.safety_category,
            "status": "Submitted",
            "priority": calculated_priority,
            "severity": ai_result.severity,
            "report_count": 1,
            "ai_summary": ai_result.summary,
        }

        # 7. Persist to complaints table
        created = await supabase_service.rest_query("complaints", method="POST", json_data=payload)
        if not created or not isinstance(created, list) or len(created) == 0:
            if data.image_url:
                await storage_service.delete_complaint_image(data.image_url)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record safety report in database.",
            )

        report_record = created[0]
        report_id = report_record["id"]

        # 8. Record initial history in complaint_updates with compensating rollback
        update_payload = {
            "complaint_id": report_id,
            "actor_id": citizen_id_str,
            "status": "Submitted",
            "remarks": f"Safety report submitted: {data.safety_category}",
        }

        history_success = False
        try:
            update_result = await supabase_service.rest_query(
                "complaint_updates", method="POST", json_data=update_payload
            )
            if update_result is not None and update_result is not False:
                history_success = True
        except Exception as exc:
            logger.error(
                f"Failed to record complaint_updates history for safety report {report_id}: {exc}",
                exc_info=True,
            )

        if not history_success:
            logger.warning(
                f"Initial history insert failed for safety report {report_id}. Initiating compensating rollback."
            )
            try:
                await supabase_service.rest_query(
                    "complaints",
                    method="DELETE",
                    params={"id": f"eq.{report_id}"},
                )
            except Exception as del_exc:
                logger.error(f"Rollback error deleting orphaned safety report {report_id}: {del_exc}")

            if data.image_url:
                try:
                    await storage_service.delete_complaint_image(data.image_url)
                except Exception:
                    pass

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Safety report creation failed: unable to record initial history. Automatic rollback completed.",
            )

        # 9. Format response
        if report_record.get("image_url"):
            report_record["image_signed_url"] = await storage_service.create_signed_url(
                report_record["image_url"]
            )
        if resolved_dept_name:
            report_record["department_name"] = resolved_dept_name
        elif report_record.get("department_id"):
            try:
                d_res = await supabase_service.rest_query(
                    "departments",
                    method="GET",
                    params={"id": f"eq.{report_record['department_id']}", "select": "name"},
                )
                if d_res and isinstance(d_res, list) and len(d_res) > 0:
                    report_record["department_name"] = d_res[0].get("name")
            except Exception:
                pass

        return SafetyReportResponse(**report_record)

    async def get_my_safety_reports(
        self,
        citizen: ProfileResponse,
        status_filter: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[SafetyReportResponse]:
        """List safety reports submitted by the authenticated citizen."""
        params: Dict[str, str] = {
            "citizen_id": f"eq.{citizen.id}",
            "safety_related": "eq.true",
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

        # Batch resolve department names
        dept_ids = {str(r["department_id"]) for r in records if r.get("department_id")}
        dept_map: Dict[str, str] = {}
        if dept_ids:
            try:
                dept_params = {
                    "id": f"in.({','.join(dept_ids)})",
                    "select": "id,name",
                }
                d_res = await supabase_service.rest_query("departments", method="GET", params=dept_params)
                if isinstance(d_res, list):
                    dept_map = {str(d["id"]): d.get("name") for d in d_res}
            except Exception as d_exc:
                logger.warning(f"Failed to batch resolve department names: {d_exc}")

        results: List[SafetyReportResponse] = []
        for r in records:
            r_dict = dict(r)
            if r_dict.get("department_id"):
                r_dict["department_name"] = dept_map.get(str(r_dict["department_id"]))
            if r_dict.get("image_url"):
                r_dict["image_signed_url"] = await storage_service.create_signed_url(r_dict["image_url"])
            results.append(SafetyReportResponse(**r_dict))

        return results

    async def list_safety_reports_for_officer(
        self,
        officer: ProfileResponse,
        department_id: Optional[UUID] = None,
        status_filter: Optional[str] = None,
        safety_category: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[SafetyReportResponse]:
        """Restricted safety register listing for designated safety officers.

        Enforces department boundaries: department-scoped officers are restricted
        to their department. City-wide officers may view all or filter by department.
        """
        if not officer.is_safety_officer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only designated safety officers may access the safety reports register.",
            )

        params: Dict[str, str] = {
            "safety_related": "eq.true",
            "order": "created_at.desc",
            "limit": str(limit),
            "offset": str(offset),
            "select": "*",
        }

        # Enforce department scoping
        if officer.department_id:
            if department_id and department_id != officer.department_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You are not authorized to view safety reports for another department.",
                )
            params["department_id"] = f"eq.{officer.department_id}"
        else:
            if department_id:
                params["department_id"] = f"eq.{department_id}"

        if status_filter:
            params["status"] = f"eq.{status_filter}"
        if safety_category:
            params["safety_category"] = f"eq.{safety_category}"

        records = await supabase_service.rest_query("complaints", method="GET", params=params)
        if not records or not isinstance(records, list):
            return []

        # Batch resolve department names
        dept_ids = {str(r["department_id"]) for r in records if r.get("department_id")}
        dept_map: Dict[str, str] = {}
        if dept_ids:
            try:
                dept_params = {
                    "id": f"in.({','.join(dept_ids)})",
                    "select": "id,name",
                }
                d_res = await supabase_service.rest_query("departments", method="GET", params=dept_params)
                if isinstance(d_res, list):
                    dept_map = {str(d["id"]): d.get("name") for d in d_res}
            except Exception as d_exc:
                logger.warning(f"Failed to batch resolve department names: {d_exc}")

        results: List[SafetyReportResponse] = []
        for r in records:
            r_dict = dict(r)
            if r_dict.get("department_id"):
                r_dict["department_name"] = dept_map.get(str(r_dict["department_id"]))
            if r_dict.get("image_url"):
                r_dict["image_signed_url"] = await storage_service.create_signed_url(r_dict["image_url"])
            results.append(SafetyReportResponse(**r_dict))

        return results

    async def get_safety_report_by_id(
        self,
        report_id: UUID,
        current_user: ProfileResponse,
    ) -> SafetyReportDetailResponse:
        """Retrieve single safety report details with chronological update timeline.

        Enforces strict RBAC:
        - Citizens can only view reports they submitted.
        - Safety officers can view reports within their authorized departmental scope.
        - Ordinary officials and workers are strictly forbidden (HTTP 403).
        """
        records = await supabase_service.rest_query(
            "complaints",
            method="GET",
            params={"id": f"eq.{report_id}", "select": "*"},
        )
        if not records or not isinstance(records, list) or len(records) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Safety report with ID '{report_id}' was not found.",
            )

        report = records[0]
        if not report.get("safety_related"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Safety report with ID '{report_id}' was not found.",
            )

        # RBAC verification
        if current_user.role == "citizen":
            if str(report.get("citizen_id")) != str(current_user.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You can only view your own safety reports.",
                )
        elif current_user.role == "official":
            if not current_user.is_safety_officer:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Only designated safety officers may view safety reports.",
                )
            if current_user.department_id and report.get("department_id"):
                if str(current_user.department_id) != str(report["department_id"]):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: You are not authorized to view safety reports outside your department.",
                    )
        else:
            # Workers and other roles are strictly prohibited
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Workers are not authorized to access safety reports.",
            )

        # Fetch chronological update history
        update_params = {
            "complaint_id": f"eq.{report_id}",
            "order": "created_at.asc",
            "select": "*",
        }
        updates_raw = await supabase_service.rest_query("complaint_updates", method="GET", params=update_params)

        updates: List[ComplaintUpdateItem] = []
        if updates_raw and isinstance(updates_raw, list):
            actor_ids = {str(u["actor_id"]) for u in updates_raw if u.get("actor_id")}
            actor_map: Dict[str, Dict[str, str]] = {}
            if actor_ids:
                try:
                    p_res = await supabase_service.rest_query(
                        "profiles",
                        method="GET",
                        params={"id": f"in.({','.join(actor_ids)})", "select": "id,full_name,role"},
                    )
                    if isinstance(p_res, list):
                        for p in p_res:
                            actor_map[str(p["id"])] = {
                                "name": p.get("full_name") or "Municipal Official",
                                "role": p.get("role") or "official",
                            }
                except Exception as p_exc:
                    logger.warning(f"Failed to resolve actor profiles: {p_exc}")

            for u in updates_raw:
                actor_info = actor_map.get(str(u.get("actor_id")), {})
                u_dict = dict(u)
                u_dict["actor_name"] = actor_info.get("name", "Municipal Official")
                u_dict["actor_role"] = actor_info.get("role", "official")
                updates.append(ComplaintUpdateItem(**u_dict))

        report_dict = dict(report)
        if report_dict.get("department_id"):
            try:
                d_res = await supabase_service.rest_query(
                    "departments",
                    method="GET",
                    params={"id": f"eq.{report_dict['department_id']}", "select": "name"},
                )
                if d_res and isinstance(d_res, list) and len(d_res) > 0:
                    report_dict["department_name"] = d_res[0].get("name")
            except Exception:
                pass

        if report_dict.get("image_url"):
            report_dict["image_signed_url"] = await storage_service.create_signed_url(
                report_dict["image_url"]
            )

        return SafetyReportDetailResponse(**report_dict, updates=updates)

    async def update_safety_investigation_status(
        self,
        report_id: UUID,
        officer: ProfileResponse,
        data: SafetyInvestigationUpdate,
    ) -> SafetyReportResponse:
        """Update safety report status, priority, severity, or department assignment.

        Validates lifecycle status transitions, enforces department boundaries,
        and applies compensating rollback if the history insert fails.
        """
        if not officer.is_safety_officer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only designated safety officers may update safety reports.",
            )

        records = await supabase_service.rest_query(
            "complaints",
            method="GET",
            params={"id": f"eq.{report_id}", "select": "*"},
        )
        if not records or not isinstance(records, list) or len(records) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Safety report with ID '{report_id}' was not found.",
            )

        report = records[0]
        if not report.get("safety_related"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Safety report with ID '{report_id}' was not found.",
            )

        # Department boundary check
        if officer.department_id:
            if report.get("department_id") and str(officer.department_id) != str(report["department_id"]):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You are not authorized to update safety reports outside your assigned department.",
                )
            if data.department_id and data.department_id != officer.department_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Department safety officers cannot assign or transfer reports to another department.",
                )

        # Lifecycle status transition validation
        current_status = report.get("status", "Submitted")
        if data.status not in VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{data.status}'. Allowed statuses are: {', '.join(sorted(VALID_STATUSES))}",
            )

        allowed_next = ALLOWED_TRANSITIONS.get(current_status, set())
        if data.status not in allowed_next:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from '{current_status}' to '{data.status}'. Allowed transitions: {', '.join(sorted(allowed_next))}",
            )

        # Validate department if provided
        target_dept_name: Optional[str] = None
        if data.department_id:
            dept_records = await supabase_service.rest_query(
                "departments",
                method="GET",
                params={"id": f"eq.{data.department_id}", "select": "id,name"},
            )
            if not dept_records or not isinstance(dept_records, list) or len(dept_records) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Target department with ID '{data.department_id}' does not exist.",
                )
            target_dept_name = dept_records[0].get("name")

        # Snapshot old state for compensating rollback
        old_status = current_status
        old_dept_id = str(report.get("department_id")) if report.get("department_id") else None
        old_priority = report.get("priority")
        old_severity = report.get("severity")

        # Prepare update payload
        update_fields: Dict[str, Any] = {
            "status": data.status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if data.department_id:
            update_fields["department_id"] = str(data.department_id)
        if data.priority:
            update_fields["priority"] = data.priority
        if data.severity is not None:
            update_fields["severity"] = data.severity

        updated = await supabase_service.rest_query(
            "complaints",
            method="PATCH",
            params={"id": f"eq.{report_id}"},
            json_data=update_fields,
        )
        if not updated or not isinstance(updated, list) or len(updated) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update safety report in database.",
            )

        # Record history entry in complaint_updates
        history_remarks = data.remarks.strip()
        if target_dept_name and data.department_id != report.get("department_id"):
            if target_dept_name not in history_remarks:
                history_remarks = f"Assigned to {target_dept_name}. {history_remarks}"

        history_payload = {
            "complaint_id": str(report_id),
            "actor_id": str(officer.id),
            "status": data.status,
            "remarks": history_remarks,
        }

        history_success = False
        try:
            h_res = await supabase_service.rest_query(
                "complaint_updates", method="POST", json_data=history_payload
            )
            if h_res is not None and h_res is not False:
                history_success = True
        except Exception as h_exc:
            logger.error(
                f"Failed to record history update for safety report {report_id}: {h_exc}",
                exc_info=True,
            )

        if not history_success:
            logger.warning(
                f"History update failed for safety report {report_id}. Initiating compensating rollback."
            )
            rollback_fields = {
                "status": old_status,
                "department_id": old_dept_id,
                "priority": old_priority,
                "severity": old_severity,
            }
            rollback_success = False
            try:
                rb_res = await supabase_service.rest_query(
                    "complaints",
                    method="PATCH",
                    params={"id": f"eq.{report_id}"},
                    json_data=rollback_fields,
                )
                if rb_res is not None and rb_res is not False:
                    rollback_success = True
            except Exception as rb_exc:
                logger.error(f"Compensating rollback failed for safety report {report_id}: {rb_exc}")

            if rollback_success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to record status update history. Status update was rolled back to previous state.",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to record status update history. Attention required: automatic rollback of safety report could not be completed.",
                )

        updated_record = updated[0]
        if updated_record.get("image_url"):
            updated_record["image_signed_url"] = await storage_service.create_signed_url(
                updated_record["image_url"]
            )
        if target_dept_name:
            updated_record["department_name"] = target_dept_name
        elif updated_record.get("department_id"):
            try:
                d_res = await supabase_service.rest_query(
                    "departments",
                    method="GET",
                    params={"id": f"eq.{updated_record['department_id']}", "select": "name"},
                )
                if d_res and isinstance(d_res, list) and len(d_res) > 0:
                    updated_record["department_name"] = d_res[0].get("name")
            except Exception:
                pass

        return SafetyReportResponse(**updated_record)


# Global singleton instance
safety_service = SafetyService()
