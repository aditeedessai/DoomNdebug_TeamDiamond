"""Comprehensive test suite for M4-08 Dashboard APIs.

Task: M4-08 Step 4 — Comprehensive Testing & Regression Verification
Sections:
  A. Schema Validation Tests
  B. Service Aggregation Tests
  C. Pagination and Failure Handling Tests
  D. Recent Preview Tests
  E. API Route & Security Tests
"""
import asyncio
import json
import sys
from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

# Add backend to path
sys.path.insert(0, "backend")

from app.api.deps import get_current_user
from app.main import app
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
from app.services.dashboard_service import (
    HIGH_SEVERITY_THRESHOLD,
    DashboardService,
    dashboard_service,
)

client = TestClient(app)


def make_user(
    role: str,
    department_id: str = None,
    user_id: str = None,
    is_safety_officer: bool = False,
) -> ProfileResponse:
    uid = user_id or str(uuid4())
    return ProfileResponse(
        id=UUID(uid) if isinstance(uid, str) else uid,
        email=f"{role}_{str(uid)[:6]}@example.com",
        full_name=f"Test {role.capitalize()}",
        role=role,
        department_id=UUID(department_id) if department_id else None,
        is_active=True,
        is_safety_officer=is_safety_officer,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


# ==============================================================================
# SECTION A: SCHEMA VALIDATION TESTS
# ==============================================================================

def test_schema_citizen_defaults():
    """A1. CitizenDashboardResponse defaults and field types."""
    resp = CitizenDashboardResponse()
    assert resp.my_total == 0
    assert resp.my_pending == 0
    assert resp.my_in_progress == 0
    assert resp.my_resolved == 0
    assert resp.my_rejected == 0
    assert resp.active_projects == 0
    assert resp.traffic_hotspots == 0
    assert resp.recent_complaints == []
    print("PASS: A1 - CitizenDashboardResponse defaults")


def test_schema_official_defaults():
    """A2. OfficialDashboardResponse defaults and field types."""
    resp = OfficialDashboardResponse()
    assert resp.total_complaints == 0
    assert resp.pending_complaints == 0
    assert resp.in_progress_complaints == 0
    assert resp.resolved_complaints == 0
    assert resp.high_priority_complaints == 0
    assert resp.department_backlog == 0
    assert resp.traffic_hotspots == 0
    assert resp.recent_complaints == []
    print("PASS: A2 - OfficialDashboardResponse defaults")


def test_schema_worker_defaults():
    """A3. WorkerDashboardResponse defaults and field types."""
    resp = WorkerDashboardResponse()
    assert resp.total_assigned_tasks == 0
    assert resp.pending_tasks == 0
    assert resp.in_progress_tasks == 0
    assert resp.completed_tasks == 0
    assert resp.recent_tasks == []
    print("PASS: A3 - WorkerDashboardResponse defaults")


def test_schema_dept_stats_defaults():
    """A4. DepartmentPerformanceStats required fields and defaults."""
    dept_id = uuid4()
    resp = DepartmentPerformanceStats(department_id=dept_id, department_name="Sanitation")
    assert resp.department_id == dept_id
    assert resp.department_name == "Sanitation"
    assert resp.total_complaints == 0
    assert resp.resolution_rate == 0.0
    print("PASS: A4 - DepartmentPerformanceStats defaults")


def test_schema_priority_breakdown_defaults():
    """A5. PriorityBreakdownResponse defaults."""
    resp = PriorityBreakdownResponse()
    assert resp.critical == 0
    assert resp.high == 0
    assert resp.medium == 0
    assert resp.low == 0
    assert resp.total == 0
    print("PASS: A5 - PriorityBreakdownResponse defaults")


def test_schema_safety_dashboard_defaults():
    """A6. SafetyDashboardResponse defaults."""
    resp = SafetyDashboardResponse()
    assert resp.total_safety_reports == 0
    assert resp.pending_investigations == 0
    assert resp.in_progress_investigations == 0
    assert resp.resolved_investigations == 0
    assert resp.high_severity_count == 0
    assert resp.category_breakdown == {}
    print("PASS: A6 - SafetyDashboardResponse defaults")


def test_schema_negative_counts_rejected():
    """A7. Negative integers rejected on count fields across schemas."""
    # Citizen
    try:
        CitizenDashboardResponse(my_total=-1)
        assert False, "Should reject negative my_total"
    except ValidationError:
        pass

    # Official
    try:
        OfficialDashboardResponse(total_complaints=-5)
        assert False, "Should reject negative total_complaints"
    except ValidationError:
        pass

    # Worker
    try:
        WorkerDashboardResponse(total_assigned_tasks=-2)
        assert False, "Should reject negative total_assigned_tasks"
    except ValidationError:
        pass

    # Priority
    try:
        PriorityBreakdownResponse(critical=-1)
        assert False, "Should reject negative critical count"
    except ValidationError:
        pass

    # Safety
    try:
        SafetyDashboardResponse(high_severity_count=-1)
        assert False, "Should reject negative high_severity_count"
    except ValidationError:
        pass

    print("PASS: A7 - Negative counts rejected across all schemas")


def test_schema_resolution_rate_bounds():
    """A8. DepartmentPerformanceStats resolution_rate strictly bounded in [0.0, 100.0]."""
    dept_id = uuid4()
    # Valid lower bound
    DepartmentPerformanceStats(department_id=dept_id, department_name="D1", resolution_rate=0.0)
    # Valid upper bound
    DepartmentPerformanceStats(department_id=dept_id, department_name="D1", resolution_rate=100.0)
    # Valid intermediate
    DepartmentPerformanceStats(department_id=dept_id, department_name="D1", resolution_rate=55.5)

    # Invalid < 0.0
    try:
        DepartmentPerformanceStats(department_id=dept_id, department_name="D1", resolution_rate=-0.1)
        assert False, "Should reject rate < 0.0"
    except ValidationError:
        pass

    # Invalid > 100.0
    try:
        DepartmentPerformanceStats(department_id=dept_id, department_name="D1", resolution_rate=100.1)
        assert False, "Should reject rate > 100.0"
    except ValidationError:
        pass
    print("PASS: A8 - Resolution rate bounded in [0.0, 100.0]")


def test_schema_recent_task_status_constraint():
    """A9. RecentTaskItem status strictly constrained to database canonical values."""
    task_id = uuid4()
    now = datetime.now()
    # Valid statuses
    for valid_st in ["Assigned", "In Progress", "Completed"]:
        t = RecentTaskItem(id=task_id, task_description="Repair", status=valid_st, created_at=now)
        assert t.status == valid_st

    # Invalid status
    for inv_st in ["Pending", "Submitted", "Closed", "Done", "invalid"]:
        try:
            RecentTaskItem(id=task_id, task_description="Repair", status=inv_st, created_at=now)
            assert False, f"Should reject invalid task status '{inv_st}'"
        except ValidationError:
            pass
    print("PASS: A9 - RecentTaskItem status strictly constrained to AssignmentStatus")


def test_schema_safety_category_breakdown_validation():
    """A10. SafetyDashboardResponse category_breakdown non-negative values."""
    # Valid positive and zero values
    SafetyDashboardResponse(category_breakdown={"Women Safety": 5, "Harassment": 0, "Lighting": 2})
    # Empty dict valid
    SafetyDashboardResponse(category_breakdown={})

    # Negative value rejected
    try:
        SafetyDashboardResponse(category_breakdown={"Women Safety": -1})
        assert False, "Should reject negative category count"
    except ValidationError:
        pass
    print("PASS: A10 - Category breakdown rejects negative values")


def test_schema_json_serialization():
    """A11. Complete JSON serialization test across all dashboard models."""
    cid = uuid4()
    now = datetime.now()
    comp_item = RecentComplaintItem(
        id=cid, title="Broken pipe", category="Water", status="Submitted", priority="Medium", created_at=now
    )
    cit_resp = CitizenDashboardResponse(my_total=1, recent_complaints=[comp_item])
    cit_json = cit_resp.model_dump_json()
    assert "Broken pipe" in cit_json

    task_item = RecentTaskItem(id=cid, task_description="Fix light", status="Assigned", created_at=now)
    wrk_resp = WorkerDashboardResponse(total_assigned_tasks=1, recent_tasks=[task_item])
    wrk_json = wrk_resp.model_dump_json()
    assert "Fix light" in wrk_json
    print("PASS: A11 - JSON serialization across schemas")


# ==============================================================================
# SECTION B: SERVICE AGGREGATION TESTS
# ==============================================================================

async def test_service_citizen_metrics_scoping():
    """B1. Citizen metrics use only the authenticated citizen's complaints."""
    service = DashboardService()
    cit_id = str(uuid4())
    cit = make_user("citizen", user_id=cit_id)

    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        # Return complaints with varied statuses
        mq.side_effect = [
            [
                {"id": "c1", "status": "Submitted"},
                {"id": "c2", "status": "Under Review"},
                {"id": "c3", "status": "Assigned"},
                {"id": "c4", "status": "In Progress"},
                {"id": "c5", "status": "Resolved"},
                {"id": "c6", "status": "Rejected"},
            ],
            [],  # preview
            [{"id": "p1"}, {"id": "p2"}],  # projects
            [{"id": "h1"}, {"id": "h2"}, {"id": "h3"}],  # hotspots
        ]
        res = await service.get_summary(cit)
        assert res.my_total == 6
        assert res.my_pending == 3  # Submitted, Under Review, Assigned
        assert res.my_in_progress == 1
        assert res.my_resolved == 1
        assert res.my_rejected == 1
        assert res.active_projects == 2
        assert res.traffic_hotspots == 3

        # Verify query was scoped to citizen_id
        call_params = mq.call_args_list[0][1]["params"]
        assert call_params["citizen_id"] == f"eq.{cit_id}"
    print("PASS: B1 - Citizen metrics scoped to authenticated citizen")


async def test_service_official_department_scoping():
    """B2. Official metrics respect department scope and calculate backlog correctly."""
    service = DashboardService()
    dept_id = str(uuid4())
    officer = make_user("official", department_id=dept_id)

    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [
                {"id": "c1", "status": "Submitted", "priority": "High", "department_id": dept_id, "safety_related": False},
                {"id": "c2", "status": "In Progress", "priority": "Critical", "department_id": dept_id, "safety_related": False},
                {"id": "c3", "status": "Resolved", "priority": "Low", "department_id": dept_id, "safety_related": False},
                {"id": "c4", "status": "Rejected", "priority": "Medium", "department_id": dept_id, "safety_related": False},
            ],
            [],  # preview
            [{"id": "h1"}],  # hotspots
        ]
        res = await service.get_summary(officer)
        assert res.total_complaints == 4
        assert res.pending_complaints == 1
        assert res.in_progress_complaints == 1
        assert res.resolved_complaints == 1
        assert res.high_priority_complaints == 2  # High + Critical
        assert res.department_backlog == 2  # c1 (Submitted) + c2 (In Progress); c3 & c4 are terminal
        assert res.traffic_hotspots == 1

        call_params = mq.call_args_list[0][1]["params"]
        assert call_params["department_id"] == f"eq.{dept_id}"
        assert call_params["safety_related"] == "eq.false"
    print("PASS: B2 - Official metrics department scoping and backlog calculation")


async def test_service_municipal_wide_official():
    """B3. Municipal-wide officials (department_id=None) can query city-wide or filter."""
    service = DashboardService()
    general_officer = make_user("official", department_id=None)

    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [[], [], []]
        await service.get_summary(general_officer)
        # Should not have department_id filter
        params = mq.call_args_list[0][1]["params"]
        assert "department_id" not in params

    filter_dept = str(uuid4())
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [[], [], []]
        await service.get_summary(general_officer, department_id=UUID(filter_dept))
        params = mq.call_args_list[0][1]["params"]
        assert params["department_id"] == f"eq.{filter_dept}"
    print("PASS: B3 - Municipal-wide official city-wide and filter capabilities")


async def test_service_department_resolution_rate_zero():
    """B4. Department statistics calculate resolution rate accurately and handle 0 complaints."""
    service = DashboardService()
    officer = make_user("official")
    d1 = str(uuid4())
    d2 = str(uuid4())

    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": d1, "name": "Roads"}, {"id": d2, "name": "Sanitation"}],
            [
                {"id": "c1", "department_id": d1, "status": "Resolved", "safety_related": False},
                {"id": "c2", "department_id": d1, "status": "In Progress", "safety_related": False},
            ],
        ]
        res = await service.get_department_stats(officer)
        assert len(res) == 2
        # d1: 1 resolved out of 2 total -> 50.0%
        assert res[0].total_complaints == 2
        assert res[0].resolved_complaints == 1
        assert res[0].resolution_rate == 50.0

        # d2: 0 complaints -> 0.0% without division-by-zero
        assert res[1].total_complaints == 0
        assert res[1].resolution_rate == 0.0
    print("PASS: B4 - Department statistics resolution rate and zero handling")


async def test_service_priority_breakdown():
    """B5. Priority breakdown counts across Critical, High, Medium, Low."""
    service = DashboardService()
    officer = make_user("official")

    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.return_value = [
            {"id": "c1", "priority": "Critical", "department_id": "d1", "safety_related": False},
            {"id": "c2", "priority": "Critical", "department_id": "d1", "safety_related": False},
            {"id": "c3", "priority": "High", "department_id": "d1", "safety_related": False},
            {"id": "c4", "priority": "Medium", "department_id": "d1", "safety_related": False},
            {"id": "c5", "priority": "Low", "department_id": "d1", "safety_related": False},
        ]
        res = await service.get_priority_breakdown(officer)
        assert res.critical == 2
        assert res.high == 1
        assert res.medium == 1
        assert res.low == 1
        assert res.total == 5
    print("PASS: B5 - Priority breakdown counts accurate")


async def test_service_safety_summary_and_threshold():
    """B6. Safety summary includes only safety reports and applies HIGH_SEVERITY_THRESHOLD=7."""
    assert HIGH_SEVERITY_THRESHOLD == 7
    service = DashboardService()
    safety_officer = make_user("official", is_safety_officer=True)

    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.return_value = [
            {"id": "s1", "status": "Submitted", "severity": 7, "safety_category": "Harassment"},
            {"id": "s2", "status": "Under Review", "severity": 8, "safety_category": "Harassment"},
            {"id": "s3", "status": "In Progress", "severity": 6, "safety_category": "Lighting"},  # < 7
            {"id": "s4", "status": "Resolved", "severity": 10, "safety_category": "Lighting"},
            {"id": "s5", "status": "Submitted", "severity": None, "safety_category": None},
        ]
        res = await service.get_safety_summary(safety_officer)
        assert res.total_safety_reports == 5
        assert res.pending_investigations == 3  # s1, s2, s5 (Submitted + Under Review)
        assert res.in_progress_investigations == 1
        assert res.resolved_investigations == 1
        assert res.high_severity_count == 3  # s1 (7), s2 (8), s4 (10)
        assert res.category_breakdown["Harassment"] == 2
        assert res.category_breakdown["Lighting"] == 2
        assert res.category_breakdown["Unspecified Safety Concern"] == 1
    print("PASS: B6 - Safety summary metrics, category breakdown, and severity threshold")


async def test_service_worker_metrics_and_unregistered():
    """B7. Worker metrics scoped to worker; unregistered worker returns clean zero cards."""
    service = DashboardService()
    # Case 1: Unregistered profile (not in workers table)
    user_unreg = make_user("worker")
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.return_value = []
        res = await service.get_summary(user_unreg)
        assert res.total_assigned_tasks == 0
        assert res.recent_tasks == []

    # Case 2: Registered worker
    user_reg = make_user("worker")
    worker_id = str(uuid4())
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": worker_id}],  # worker lookup
            [
                {"id": "a1", "status": "Assigned"},
                {"id": "a2", "status": "In Progress"},
                {"id": "a3", "status": "Completed"},
            ],
            [],  # recent preview
        ]
        res = await service.get_summary(user_reg)
        assert res.total_assigned_tasks == 3
        assert res.pending_tasks == 1
        assert res.in_progress_tasks == 1
        assert res.completed_tasks == 1
    print("PASS: B7 - Worker metrics scoping and unregistered profile handling")


# ==============================================================================
# SECTION C: PAGINATION AND FAILURE HANDLING TESTS
# ==============================================================================

async def test_pagination_record_counts():
    """C1. Pagination handles 0, 1000, 2000, and 2500 records with stable id.asc ordering."""
    service = DashboardService()

    # 0 records
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.return_value = []
        res = await service._fetch_all_records("complaints", {})
        assert len(res) == 0
        assert mq.call_count == 1
        assert mq.call_args_list[0][1]["params"]["order"] == "id.asc"

    # 1,000 records
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [[{"id": f"c_{i}"} for i in range(1000)], []]
        res = await service._fetch_all_records("complaints", {})
        assert len(res) == 1000
        assert mq.call_count == 2
        assert mq.call_args_list[0][1]["params"]["offset"] == "0"
        assert mq.call_args_list[1][1]["params"]["offset"] == "1000"

    # 2,000 records
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": f"c_{i}"} for i in range(1000)],
            [{"id": f"c_{1000+i}"} for i in range(1000)],
            [],
        ]
        res = await service._fetch_all_records("complaints", {})
        assert len(res) == 2000
        assert mq.call_count == 3
        assert mq.call_args_list[2][1]["params"]["offset"] == "2000"

    # 2,500 records
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": f"c_{i}"} for i in range(1000)],
            [{"id": f"c_{1000+i}"} for i in range(1000)],
            [{"id": f"c_{2000+i}"} for i in range(500)],
        ]
        res = await service._fetch_all_records("complaints", {})
        assert len(res) == 2500
        assert mq.call_count == 3
    print("PASS: C1 - Pagination handles 0, 1000, 2000, 2500 records cleanly")


async def test_pagination_ordering_on_all_six_queries():
    """C2. Stable id.asc ordering applied on all six paginated query types."""
    service = DashboardService()

    # 1. Citizen summary
    cit = make_user("citizen")
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [[], [], [], []]
        await service.get_summary(cit)
        assert mq.call_args_list[0][1]["params"]["order"] == "id.asc"

    # 2. Official summary
    off = make_user("official")
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [[], [], []]
        await service.get_summary(off)
        assert mq.call_args_list[0][1]["params"]["order"] == "id.asc"

    # 3. Worker summary
    wrk = make_user("worker")
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [[{"id": "w1"}], [], []]
        await service.get_summary(wrk)
        assert mq.call_args_list[1][1]["params"]["order"] == "id.asc"

    # 4. Department stats
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [[{"id": str(uuid4()), "name": "D"}], []]
        await service.get_department_stats(off)
        assert mq.call_args_list[1][1]["params"]["order"] == "id.asc"

    # 5. Priority breakdown
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.return_value = []
        await service.get_priority_breakdown(off)
        assert mq.call_args_list[0][1]["params"]["order"] == "id.asc"

    # 6. Safety summary
    safe_off = make_user("official", is_safety_officer=True)
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.return_value = []
        await service.get_safety_summary(safe_off)
        assert mq.call_args_list[0][1]["params"]["order"] == "id.asc"

    print("PASS: C2 - Stable id.asc ordering verified on all 6 paginated query types")


async def test_failure_handling_503_propagation():
    """C3. Outages across all database calls strictly propagate HTTP 503."""
    service = DashboardService()
    cit = make_user("citizen")

    # Failure on page 1 of pagination
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.return_value = None
        try:
            await service.get_summary(cit)
            assert False, "Should raise 503"
        except HTTPException as exc:
            assert exc.status_code == 503

    # Failure on page 2 of pagination
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [[{"id": f"c_{i}"} for i in range(1000)], None]
        try:
            await service.get_summary(cit)
            assert False, "Should raise 503 on page 2 failure"
        except HTTPException as exc:
            assert exc.status_code == 503

    # Failure on recent preview
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [[], None]  # agg succeeds, preview fails
        try:
            await service.get_summary(cit)
            assert False, "Should raise 503 on preview failure"
        except HTTPException as exc:
            assert exc.status_code == 503

    # Failure on projects query
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [[], [], None]  # agg & preview succeed, projects fails
        try:
            await service.get_summary(cit)
            assert False, "Should raise 503 on projects failure"
        except HTTPException as exc:
            assert exc.status_code == 503

    # Failure on hotspots query
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [[], [], [], None]  # agg, preview, projects succeed, hotspots fails
        try:
            await service.get_summary(cit)
            assert False, "Should raise 503 on hotspots failure"
        except HTTPException as exc:
            assert exc.status_code == 503

    # Failure on worker lookup
    wrk = make_user("worker")
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.return_value = None
        try:
            await service.get_summary(wrk)
            assert False, "Should raise 503 on worker lookup failure"
        except HTTPException as exc:
            assert exc.status_code == 503

    print("PASS: C3 - Failures across all queries strictly propagate HTTP 503")


# ==============================================================================
# SECTION D: RECENT PREVIEW TESTS
# ==============================================================================

async def test_recent_previews_isolation_and_minimal_fields():
    """D1. Recent previews use server-side limit=5, created_at.desc, and minimal projection."""
    service = DashboardService()

    # Citizen preview
    cit = make_user("citizen")
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [[], [], [], []]
        await service.get_summary(cit)
        prev_p = mq.call_args_list[1][1]["params"]
        assert prev_p["limit"] == "5"
        assert prev_p["order"] == "created_at.desc"
        assert "description" not in prev_p["select"]
        assert "location" not in prev_p["select"]
        assert "citizen_id" not in prev_p["select"]

    # Official preview
    off = make_user("official", department_id=str(uuid4()))
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [[], [], []]
        await service.get_summary(off)
        prev_p = mq.call_args_list[1][1]["params"]
        assert prev_p["limit"] == "5"
        assert prev_p["order"] == "created_at.desc"
        assert prev_p["safety_related"] == "eq.false"

    # Worker preview
    wrk = make_user("worker")
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [[{"id": "w1"}], [], []]
        await service.get_summary(wrk)
        prev_p = mq.call_args_list[2][1]["params"]
        assert prev_p["limit"] == "5"
        assert prev_p["order"] == "created_at.desc"
        assert prev_p["select"] == "id,task_description,status,created_at"

    print("PASS: D1 - Recent previews server-side bounded, ordered, and field-minimized")


# ==============================================================================
# SECTION E: API ROUTE TESTS
# ==============================================================================

def test_routes_authentication_required():
    """E1. Every route rejects unauthenticated requests with 401/403."""
    app.dependency_overrides.clear()
    for path in ["/summary", "/departments", "/priorities", "/safety"]:
        res = client.get(f"/api/v1/dashboard{path}")
        assert res.status_code in (401, 403), f"Expected 401/403 for {path}, got {res.status_code}"
    print("PASS: E1 - Unauthenticated requests rejected on all routes")


def test_routes_role_discriminated_summary():
    """E2. GET /summary returns role-appropriate response schemas."""
    # Citizen
    cit = make_user("citizen")
    app.dependency_overrides[get_current_user] = lambda: cit
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [[{"id": str(uuid4()), "status": "Submitted"}], [], [], []]
        res = client.get("/api/v1/dashboard/summary")
        assert res.status_code == 200
        assert "my_total" in res.json()
        assert "total_complaints" not in res.json()

    # Official
    off = make_user("official")
    app.dependency_overrides[get_current_user] = lambda: off
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [[{"id": str(uuid4()), "status": "Submitted", "priority": "Low", "safety_related": False}], [], []]
        res = client.get("/api/v1/dashboard/summary")
        assert res.status_code == 200
        assert "total_complaints" in res.json()
        assert "my_total" not in res.json()

    # Worker
    wrk = make_user("worker")
    app.dependency_overrides[get_current_user] = lambda: wrk
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [[{"id": str(uuid4())}], [{"id": str(uuid4()), "status": "Assigned"}], []]
        res = client.get("/api/v1/dashboard/summary")
        assert res.status_code == 200
        assert "total_assigned_tasks" in res.json()
        assert "total_complaints" not in res.json()

    print("PASS: E2 - Role-discriminated summary responses verified")


def test_routes_department_and_priority_role_enforcement():
    """E3. GET /departments and GET /priorities restricted strictly to officials."""
    cit = make_user("citizen")
    wrk = make_user("worker")

    for u in [cit, wrk]:
        app.dependency_overrides[get_current_user] = lambda u=u: u
        assert client.get("/api/v1/dashboard/departments").status_code == 403
        assert client.get("/api/v1/dashboard/priorities").status_code == 403

    off = make_user("official")
    app.dependency_overrides[get_current_user] = lambda: off
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": str(uuid4()), "name": "Health"}],
            [],
        ]
        assert client.get("/api/v1/dashboard/departments").status_code == 200

    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.return_value = []
        assert client.get("/api/v1/dashboard/priorities").status_code == 200

    print("PASS: E3 - Departments and priorities restricted strictly to officials")


def test_routes_safety_dashboard_role_enforcement():
    """E4. GET /safety restricted exclusively to safety officers."""
    cit = make_user("citizen")
    wrk = make_user("worker")
    ord_off = make_user("official", is_safety_officer=False)

    for u in [cit, wrk, ord_off]:
        app.dependency_overrides[get_current_user] = lambda u=u: u
        assert client.get("/api/v1/dashboard/safety").status_code == 403

    safe_off = make_user("official", is_safety_officer=True)
    app.dependency_overrides[get_current_user] = lambda: safe_off
    with patch("app.services.dashboard_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.return_value = []
        res = client.get("/api/v1/dashboard/safety")
        assert res.status_code == 200
        assert "total_safety_reports" in res.json()

    print("PASS: E4 - Safety dashboard restricted strictly to safety officers")


def test_routes_cross_department_access_blocked():
    """E5. Cross-department queries by scoped officials return HTTP 403."""
    dept1 = str(uuid4())
    dept2 = str(uuid4())
    officer = make_user("official", department_id=dept1)
    app.dependency_overrides[get_current_user] = lambda: officer

    assert client.get(f"/api/v1/dashboard/summary?department_id={dept2}").status_code == 403
    assert client.get(f"/api/v1/dashboard/departments?department_id={dept2}").status_code == 403
    assert client.get(f"/api/v1/dashboard/priorities?department_id={dept2}").status_code == 403

    print("PASS: E5 - Cross-department access blocked with HTTP 403")


def test_routes_openapi_spec():
    """E6. OpenAPI specification includes all 4 dashboard endpoints with exact tags and methods."""
    openapi = app.openapi()
    paths = openapi["paths"]
    for ep in ["/api/v1/dashboard/summary", "/api/v1/dashboard/departments", "/api/v1/dashboard/priorities", "/api/v1/dashboard/safety"]:
        assert ep in paths, f"Path {ep} missing in OpenAPI"
        assert "get" in paths[ep], f"GET method missing for {ep}"
        assert "dashboard" in paths[ep]["get"]["tags"]
    print("PASS: E6 - OpenAPI specification verified for all 4 dashboard endpoints")


# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================

async def run_async_tests():
    print("\n--- Running Section B: Service Aggregation Tests ---")
    await test_service_citizen_metrics_scoping()
    await test_service_official_department_scoping()
    await test_service_municipal_wide_official()
    await test_service_department_resolution_rate_zero()
    await test_service_priority_breakdown()
    await test_service_safety_summary_and_threshold()
    await test_service_worker_metrics_and_unregistered()

    print("\n--- Running Section C: Pagination and Failure Handling Tests ---")
    await test_pagination_record_counts()
    await test_pagination_ordering_on_all_six_queries()
    await test_failure_handling_503_propagation()

    print("\n--- Running Section D: Recent Preview Tests ---")
    await test_recent_previews_isolation_and_minimal_fields()


def main():
    print("=" * 75)
    print("M4-08 COMPREHENSIVE DASHBOARD TEST SUITE")
    print("=" * 75)

    print("\n--- Running Section A: Schema Validation Tests ---")
    test_schema_citizen_defaults()
    test_schema_official_defaults()
    test_schema_worker_defaults()
    test_schema_dept_stats_defaults()
    test_schema_priority_breakdown_defaults()
    test_schema_safety_dashboard_defaults()
    test_schema_negative_counts_rejected()
    test_schema_resolution_rate_bounds()
    test_schema_recent_task_status_constraint()
    test_schema_safety_category_breakdown_validation()
    test_schema_json_serialization()

    asyncio.run(run_async_tests())

    print("\n--- Running Section E: API Route & Security Tests ---")
    test_routes_authentication_required()
    test_routes_role_discriminated_summary()
    test_routes_department_and_priority_role_enforcement()
    test_routes_safety_dashboard_role_enforcement()
    test_routes_cross_department_access_blocked()
    test_routes_openapi_spec()

    app.dependency_overrides.clear()
    print("\n" + "=" * 75)
    print("ALL M4-08 COMPREHENSIVE TESTS PASSED SUCCESSFULLY (27/27 TEST GROUPS)")
    print("=" * 75)


if __name__ == "__main__":
    main()
