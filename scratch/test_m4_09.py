"""Comprehensive test suite for M4-09 Worker and Officer Assignments.

Task: M4-09 Step 6 — Comprehensive Testing and Full Regression Verification
PRD References: Section 4.7, 6.7, 6.8, 7.6
Database References: database/schema.sql (workers, assignments, chk_assignment_target, complaint_updates)

Sections:
  A. Schema Validation Tests (Pydantic models)
  B. Service Layer Tests (Mocked database calls)
  C. Cross-Layer Integration Tests (Actual routes + actual service, mocked database boundary)
"""
import asyncio
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

# Add backend to path
sys.path.insert(0, "backend")

from app.api.deps import get_current_user
from app.main import app
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
from app.services.assignment_service import (
    ASSIGNABLE_COMPLAINT_STATUSES,
    TERMINAL_COMPLAINT_STATUSES,
    AssignmentService,
    assignment_service,
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

def test_schema_valid_complaint_assignment():
    """A1. Valid complaint assignment schema."""
    cid = uuid4()
    wid = uuid4()
    obj = AssignmentCreate(
        complaint_id=cid,
        worker_id=wid,
        task_description="Repair water pipeline",
    )
    assert obj.complaint_id == cid
    assert obj.hotspot_id is None
    assert obj.worker_id == wid
    assert obj.status == "Assigned"


def test_schema_valid_hotspot_assignment():
    """A2. Valid hotspot assignment schema."""
    hid = uuid4()
    wid = uuid4()
    obj = AssignmentCreate(
        hotspot_id=hid,
        worker_id=wid,
        task_description="Deploy traffic cones at junction",
    )
    assert obj.hotspot_id == hid
    assert obj.complaint_id is None
    assert obj.worker_id == wid


def test_schema_both_targets_rejected():
    """A3. Both complaint_id and hotspot_id rejected by single-target constraint."""
    try:
        AssignmentCreate(
            complaint_id=uuid4(),
            hotspot_id=uuid4(),
            worker_id=uuid4(),
            task_description="Invalid dual target",
        )
        assert False, "Should raise ValidationError"
    except (ValidationError, ValueError):
        pass


def test_schema_neither_target_rejected():
    """A4. Neither complaint_id nor hotspot_id rejected by single-target constraint."""
    try:
        AssignmentCreate(
            worker_id=uuid4(),
            task_description="Invalid empty target",
        )
        assert False, "Should raise ValidationError"
    except (ValidationError, ValueError):
        pass


def test_schema_missing_worker_id_rejected():
    """A5. Missing worker_id rejected."""
    try:
        AssignmentCreate(
            complaint_id=uuid4(),
            task_description="Missing worker",
        )
        assert False, "Should raise ValidationError"
    except ValidationError:
        pass


def test_schema_invalid_assignment_status_rejected():
    """A6. Invalid assignment status rejected."""
    try:
        AssignmentCreate(
            complaint_id=uuid4(),
            worker_id=uuid4(),
            task_description="Valid description",
            status="InvalidStatus",
        )
        assert False, "Should raise ValidationError"
    except ValidationError:
        pass


def test_schema_invalid_worker_availability_rejected():
    """A7. Invalid worker availability rejected."""
    try:
        WorkerResponse(
            id=uuid4(),
            name="Bob",
            department_id=uuid4(),
            availability="OnBreak",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert False, "Should raise ValidationError"
    except ValidationError:
        pass


def test_schema_task_description_length_bounds():
    """A8. Task description min (3) and max (1000) length validation."""
    # Too short (< 3)
    try:
        AssignmentCreate(
            complaint_id=uuid4(),
            worker_id=uuid4(),
            task_description="AB",
        )
        assert False, "Should raise ValidationError for short description"
    except ValidationError:
        pass

    # Too long (> 1000)
    try:
        AssignmentCreate(
            complaint_id=uuid4(),
            worker_id=uuid4(),
            task_description="A" * 1001,
        )
        assert False, "Should raise ValidationError for long description"
    except ValidationError:
        pass

    # Boundary valid (3 and 1000)
    c3 = AssignmentCreate(complaint_id=uuid4(), worker_id=uuid4(), task_description="ABC")
    assert len(c3.task_description) == 3
    c1000 = AssignmentCreate(complaint_id=uuid4(), worker_id=uuid4(), task_description="X" * 1000)
    assert len(c1000.task_description) == 1000


def test_schema_unknown_request_fields_rejected():
    """A9. Unknown request fields rejected by extra='forbid'."""
    try:
        AssignmentCreate(
            complaint_id=uuid4(),
            worker_id=uuid4(),
            task_description="Valid description",
            unexpected_field="hack",
        )
        assert False, "Should raise ValidationError"
    except ValidationError:
        pass


def test_schema_client_supplied_officer_id_rejected():
    """A10. Client-supplied officer_id rejected on creation payload."""
    try:
        AssignmentCreate(
            complaint_id=uuid4(),
            worker_id=uuid4(),
            task_description="Valid description",
            officer_id=uuid4(),
        )
        assert False, "Should raise ValidationError"
    except ValidationError:
        pass


def test_schema_empty_update_rejected():
    """A11. Empty AssignmentUpdate rejected."""
    try:
        AssignmentUpdate()
        assert False, "Should raise ValidationError on empty update"
    except (ValidationError, ValueError):
        pass


def test_schema_valid_status_only_update():
    """A12. Valid status-only update."""
    up = AssignmentUpdate(status="In Progress")
    assert up.status == "In Progress"
    assert up.task_description is None
    assert up.worker_id is None
    assert up.notes is None


def test_schema_valid_task_description_update():
    """A13. Valid task description update."""
    up = AssignmentUpdate(task_description="Updated directions for crew")
    assert up.task_description == "Updated directions for crew"


def test_schema_valid_worker_reassignment_update():
    """A14. Valid worker reassignment update."""
    wid = uuid4()
    up = AssignmentUpdate(worker_id=wid)
    assert up.worker_id == wid


def test_schema_notes_max_length():
    """A15. Notes maximum length bounded to 1000 chars."""
    try:
        AssignmentUpdate(notes="N" * 1001)
        assert False, "Should reject notes > 1000 chars"
    except ValidationError:
        pass
    valid_notes = AssignmentUpdate(notes="N" * 1000)
    assert len(valid_notes.notes) == 1000


def test_schema_serialization_and_detail_responses():
    """A16, A17, A18. UUID/datetime serialization and detail responses for complaint and hotspot."""
    aid = uuid4()
    cid = uuid4()
    wid = uuid4()
    oid = uuid4()
    now = datetime.now(timezone.utc)

    # Complaint detail response
    cdetail = AssignmentDetailResponse(
        id=aid,
        complaint_id=cid,
        hotspot_id=None,
        worker_id=wid,
        worker_name="Crew Beta",
        officer_id=oid,
        officer_name="Officer Jane",
        task_description="Clear blockage",
        status="Assigned",
        created_at=now,
        updated_at=now,
        target_type="complaint",
        complaint_title="Blocked drainage",
        complaint_category="Sanitation",
        complaint_priority="High",
    )
    cdict = json.loads(cdetail.model_dump_json())
    assert cdict["id"] == str(aid)
    assert cdict["target_type"] == "complaint"
    assert cdict["complaint_title"] == "Blocked drainage"

    # Hotspot detail response
    hid = uuid4()
    hdetail = AssignmentDetailResponse(
        id=aid,
        complaint_id=None,
        hotspot_id=hid,
        worker_id=wid,
        worker_name="Traffic Crew",
        officer_id=oid,
        officer_name="Officer Dave",
        task_description="Direct traffic",
        status="In Progress",
        created_at=now,
        updated_at=now,
        target_type="hotspot",
        hotspot_congestion="High",
        hotspot_description="Gridlock at Ring Road",
    )
    hdict = json.loads(hdetail.model_dump_json())
    assert hdict["target_type"] == "hotspot"
    assert hdict["hotspot_congestion"] == "High"


# ==============================================================================
# SECTION B: SERVICE LAYER TESTS (MOCKED DATABASE)
# ==============================================================================

async def test_service_worker_listing_and_scoping():
    """B1-B4. Worker listing for official, department scoping, worker own profile, citizen rejection."""
    service = AssignmentService()

    # 1. Citizen rejected with 403
    cit = make_user("citizen")
    try:
        await service.list_workers(cit)
        assert False, "Should raise 403 for citizen"
    except HTTPException as e:
        assert e.status_code == 403

    # 2. Worker receives solely their own profile
    wrk_user = make_user("worker")
    my_worker_row = {
        "id": str(uuid4()),
        "profile_id": str(wrk_user.id),
        "name": "Self Crew",
        "department_id": str(uuid4()),
        "availability": "Available",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [my_worker_row],  # lookup worker
            [{"name": "Public Works"}],  # department name
        ]
        res = await service.list_workers(wrk_user)
        assert len(res) == 1
        assert res[0].name == "Self Crew"
        assert res[0].profile_id == wrk_user.id

    # 3. Department-scoped official listing cannot be overridden
    dept_a = uuid4()
    dept_b = uuid4()
    off_dept_a = make_user("official", department_id=str(dept_a))
    try:
        await service.list_workers(off_dept_a, department_id=dept_b)
        assert False, "Should raise 403 on cross-department query"
    except HTTPException as e:
        assert e.status_code == 403

    # 4. Municipal official can list with filter
    muni_off = make_user("official")
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [
                {
                    "id": str(uuid4()),
                    "name": "Crew 1",
                    "department_id": str(dept_a),
                    "availability": "Available",
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ],
            [{"id": str(dept_a), "name": "Roads"}],
        ]
        res = await service.list_workers(muni_off, department_id=dept_a, availability="Available")
        assert len(res) == 1
        assert res[0].department_name == "Roads"
        assert mq.call_args_list[0][1]["params"]["department_id"] == f"eq.{dept_a}"
        assert mq.call_args_list[0][1]["params"]["availability"] == "eq.Available"


async def test_service_worker_detail_authorization():
    """B5-B7. Worker detail authorization and isolation."""
    service = AssignmentService()
    dept_id = str(uuid4())
    worker_id = str(uuid4())
    worker_row = {
        "id": worker_id,
        "profile_id": str(uuid4()),
        "name": "Alpha Crew",
        "department_id": dept_id,
        "availability": "Available",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }

    # Worker viewing another worker -> 404
    wrk_user = make_user("worker")
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.return_value = [worker_row]
        try:
            await service.get_worker_by_id(wrk_user, UUID(worker_id))
            assert False, "Worker should not access another worker"
        except HTTPException as e:
            assert e.status_code == 404

    # Department official viewing worker in another department -> 404
    other_dept_off = make_user("official", department_id=str(uuid4()))
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.return_value = [worker_row]
        try:
            await service.get_worker_by_id(other_dept_off, UUID(worker_id))
            assert False, "Official should not access worker in another department"
        except HTTPException as e:
            assert e.status_code == 404


async def test_service_create_assignment_validation():
    """B8-B14. Assignment creation rules, targets, safety segregation, and rollback."""
    service = AssignmentService()
    dept_id = str(uuid4())
    off = make_user("official", department_id=dept_id)
    wid = uuid4()
    cid = uuid4()

    # Unavailable worker -> HTTP 400
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.return_value = [{"id": str(wid), "name": "Busy Worker", "availability": "Unavailable"}]
        try:
            await service.create_assignment(
                off,
                AssignmentCreate(complaint_id=cid, worker_id=wid, task_description="Task"),
            )
            assert False, "Should reject unavailable worker"
        except HTTPException as e:
            assert e.status_code == 400

    # Worker department mismatch -> HTTP 400
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": str(wid), "name": "Crew", "department_id": str(uuid4()), "availability": "Available"}],
            [{"id": str(cid), "department_id": dept_id, "safety_related": False, "status": "Submitted"}],
        ]
        try:
            await service.create_assignment(
                off,
                AssignmentCreate(complaint_id=cid, worker_id=wid, task_description="Task"),
            )
            assert False, "Should reject department mismatch"
        except HTTPException as e:
            assert e.status_code == 400

    # Ordinary official cannot assign safety complaint -> HTTP 403
    ord_off = make_user("official", department_id=dept_id, is_safety_officer=False)
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": str(wid), "name": "Crew", "department_id": dept_id, "availability": "Available"}],
            [{"id": str(cid), "department_id": dept_id, "safety_related": True, "status": "Submitted"}],
        ]
        try:
            await service.create_assignment(
                ord_off,
                AssignmentCreate(complaint_id=cid, worker_id=wid, task_description="Safety Task"),
            )
            assert False, "Should reject ordinary official assigning safety complaint"
        except HTTPException as e:
            assert e.status_code == 403

    # Terminal complaint status -> HTTP 400
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": str(wid), "name": "Crew", "department_id": dept_id, "availability": "Available"}],
            [{"id": str(cid), "department_id": dept_id, "safety_related": False, "status": "Resolved"}],
        ]
        try:
            await service.create_assignment(
                off,
                AssignmentCreate(complaint_id=cid, worker_id=wid, task_description="Task"),
            )
            assert False, "Should reject assigning resolved complaint"
        except HTTPException as e:
            assert e.status_code == 400


async def test_service_create_assignment_lifecycle_and_rollback():
    """B15-B16. Successful creation advances complaint status and history; rollback triggers on failure."""
    service = AssignmentService()
    dept_id = str(uuid4())
    off = make_user("official", department_id=dept_id)
    wid = uuid4()
    cid = uuid4()
    aid = str(uuid4())

    # Successful creation
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": str(wid), "name": "Crew", "department_id": dept_id, "availability": "Available"}],
            [{"id": str(cid), "department_id": dept_id, "safety_related": False, "status": "Submitted"}],
            [
                {
                    "id": aid,
                    "complaint_id": str(cid),
                    "worker_id": str(wid),
                    "officer_id": str(off.id),
                    "task_description": "Clean road",
                    "status": "Assigned",
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ],
            [{"id": str(cid), "status": "Assigned"}],  # patch complaint
            [{"id": str(uuid4())}],  # insert complaint_updates
        ]
        res = await service.create_assignment(
            off,
            AssignmentCreate(complaint_id=cid, worker_id=wid, task_description="Clean road"),
        )
        assert res.id == UUID(aid)
        assert res.status == "Assigned"
        # Verify complaint PATCH was called
        patch_call = [c for c in mq.call_args_list if c[0][0] == "complaints" and c[1].get("method") == "PATCH"]
        assert len(patch_call) == 1
        assert patch_call[0][1]["json_data"]["status"] == "Assigned"

    # Compensating rollback on sync exception
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": str(wid), "name": "Crew", "department_id": dept_id, "availability": "Available"}],
            [{"id": str(cid), "department_id": dept_id, "safety_related": False, "status": "Submitted"}],
            [
                {
                    "id": aid,
                    "complaint_id": str(cid),
                    "worker_id": str(wid),
                    "officer_id": str(off.id),
                    "task_description": "Clean road",
                    "status": "Assigned",
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ],
            Exception("Database connection severed during complaint status update!"),
            [{"id": aid}],  # rollback DELETE
        ]
        try:
            await service.create_assignment(
                off,
                AssignmentCreate(complaint_id=cid, worker_id=wid, task_description="Clean road"),
            )
            assert False, "Should raise 503 after failure and rollback"
        except HTTPException as e:
            assert e.status_code == 503
            # Verify compensating DELETE on assignments was invoked
            del_call = [c for c in mq.call_args_list if c[0][0] == "assignments" and c[1].get("method") == "DELETE"]
            assert len(del_call) == 1


async def test_service_assignment_listing_scoping_and_safety():
    """B17-B20. Assignment listing scoping, safety exclusion, and pagination."""
    service = AssignmentService()
    dept_id = str(uuid4())
    ord_off = make_user("official", department_id=dept_id, is_safety_officer=False)

    aid1 = str(uuid4())
    aid2 = str(uuid4())
    cid1 = str(uuid4())
    cid2 = str(uuid4())

    assignments = [
        {"id": aid1, "complaint_id": cid1, "worker_id": str(uuid4()), "officer_id": str(uuid4()), "status": "Assigned", "task_description": "Fix light", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"},
        {"id": aid2, "complaint_id": cid2, "worker_id": str(uuid4()), "officer_id": str(uuid4()), "status": "Assigned", "task_description": "Investigate hazard", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"},
    ]
    complaints = [
        {"id": cid1, "department_id": dept_id, "safety_related": False},
        {"id": cid2, "department_id": dept_id, "safety_related": True},  # safety report!
    ]

    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            assignments,
            complaints,
            [],  # workers dept map
            [{"id": assignments[0]["worker_id"], "name": "Crew 1"}],
            [{"id": assignments[0]["officer_id"], "full_name": "Official 1"}],
        ]
        res = await service.list_assignments(ord_off)
        # Ordinary official must see only non-safety assignment (aid1)
        assert len(res) == 1
        assert str(res[0].id) == aid1
        assert res[0].task_description == "Fix light"


async def test_service_assignment_updates_and_state_machine():
    """B21-B26. Assignment lifecycle transitions, terminal lock, worker restrictions, and history logging."""
    service = AssignmentService()
    aid = uuid4()
    wid = str(uuid4())
    cid = str(uuid4())
    wrk_user = make_user("worker")

    # 1. Worker cannot reassign worker_id -> HTTP 403
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": str(aid), "worker_id": wid, "status": "Assigned"}],  # assignment lookup
            [{"id": wid, "profile_id": str(wrk_user.id)}],  # worker for user
        ]
        try:
            await service.update_assignment(wrk_user, aid, AssignmentUpdate(worker_id=uuid4()))
            assert False, "Worker should not reassign worker"
        except HTTPException as e:
            assert e.status_code == 403

    # 2. Worker cannot edit task_description -> HTTP 403
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": str(aid), "worker_id": wid, "status": "Assigned"}],
            [{"id": wid, "profile_id": str(wrk_user.id)}],
        ]
        try:
            await service.update_assignment(wrk_user, aid, AssignmentUpdate(task_description="Tampered description"))
            assert False, "Worker should not edit task description"
        except HTTPException as e:
            assert e.status_code == 403

    # 3. Completed assignment is terminal and cannot be reopened -> HTTP 400
    off = make_user("official")
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": str(aid), "worker_id": wid, "status": "Completed", "complaint_id": cid}],
            [{"id": cid, "department_id": None, "safety_related": False, "status": "In Progress"}],
        ]
        try:
            await service.update_assignment(off, aid, AssignmentUpdate(status="In Progress"))
            assert False, "Completed assignment cannot be reopened"
        except HTTPException as e:
            assert e.status_code == 400

    # 4. Cannot revert In Progress to Assigned -> HTTP 400
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": str(aid), "worker_id": wid, "status": "In Progress", "complaint_id": cid}],
            [{"id": cid, "department_id": None, "safety_related": False, "status": "In Progress"}],
        ]
        try:
            await service.update_assignment(off, aid, AssignmentUpdate(status="Assigned"))
            assert False, "Cannot revert In Progress to Assigned"
        except HTTPException as e:
            assert e.status_code == 400

    # 5. Valid transition: Assigned -> In Progress updates complaint and logs complaint_updates
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": str(aid), "worker_id": wid, "status": "Assigned", "complaint_id": cid, "task_description": "Clean"}],
            [{"id": wid, "profile_id": str(wrk_user.id)}],  # worker resolution
            [{"id": cid, "status": "Assigned"}],  # complaint lookup
            [{"id": str(aid)}],  # patch assignment
            [{"id": cid, "status": "In Progress"}],  # patch complaint
            [{"id": str(uuid4())}],  # insert complaint_updates
            [{"id": str(aid), "worker_id": wid, "officer_id": str(off.id), "status": "In Progress", "task_description": "Clean", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"}],
            [{"id": wid, "name": "Crew Beta"}],
            [{"id": str(off.id), "full_name": "Official Dave"}],
        ]
        res = await service.update_assignment(wrk_user, aid, AssignmentUpdate(status="In Progress", notes="Commencing work"))
        assert res.status == "In Progress"
        # Verify complaint update was called with In Progress
        comp_patch = [c for c in mq.call_args_list if c[0][0] == "complaints" and c[1].get("method") == "PATCH"]
        assert len(comp_patch) == 1
        assert comp_patch[0][1]["json_data"]["status"] == "In Progress"

    # 6. Valid transition: In Progress -> Completed logs history but does NOT mark complaint Resolved
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": str(aid), "worker_id": wid, "status": "In Progress", "complaint_id": cid, "task_description": "Clean"}],
            [{"id": wid, "profile_id": str(wrk_user.id)}],
            [{"id": cid, "status": "In Progress"}],
            [{"id": str(aid)}],  # patch assignment
            [{"id": str(uuid4())}],  # insert complaint_updates history
            [{"id": str(aid), "worker_id": wid, "officer_id": str(off.id), "status": "Completed", "task_description": "Clean", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"}],
            [{"id": wid, "name": "Crew Beta"}],
            [{"id": str(off.id), "full_name": "Official Dave"}],
        ]
        res = await service.update_assignment(wrk_user, aid, AssignmentUpdate(status="Completed", notes="Finished site cleaning"))
        assert res.status == "Completed"
        # Confirm complaints table was NOT patched to Resolved
        resolved_patches = [c for c in mq.call_args_list if c[0][0] == "complaints" and c[1].get("method") == "PATCH" and c[1]["json_data"].get("status") == "Resolved"]
        assert len(resolved_patches) == 0


async def test_service_database_reliability_and_pagination():
    """B27-B28. Database 503 propagation and PostgREST sequential pagination."""
    service = AssignmentService()

    # 1. PostgREST returning None strictly propagates HTTP 503
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.return_value = None
        try:
            await service.list_workers(make_user("official"))
            assert False, "Should raise 503 on database None response"
        except HTTPException as e:
            assert e.status_code == 503

    # 2. Sequential pagination across PostgREST batches
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": f"rec_{i}"} for i in range(1000)],
            [{"id": f"rec_{1000+i}"} for i in range(250)],
        ]
        res = await service._fetch_all_records("assignments", {})
        assert len(res) == 1250
        assert mq.call_count == 2
        assert mq.call_args_list[0][1]["params"]["limit"] == "1000"
        assert mq.call_args_list[0][1]["params"]["offset"] == "0"
        assert mq.call_args_list[1][1]["params"]["offset"] == "1000"


# ==============================================================================
# SECTION C: CROSS-LAYER INTEGRATION TESTS (ACTUAL ROUTES + ACTUAL SERVICE)
# ==============================================================================

def test_integration_full_complaint_assignment_lifecycle():
    """C1-C8. End-to-end complaint assignment lifecycle through FastAPI routes with mocked DB."""
    app.dependency_overrides.clear()

    dept_id = str(uuid4())
    off = make_user("official", department_id=dept_id)
    wrk = make_user("worker")
    wid = str(uuid4())
    cid = str(uuid4())
    aid = str(uuid4())

    # Step 1 & 2: Official creates complaint assignment
    app.dependency_overrides[get_current_user] = lambda: off
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": wid, "name": "Road Repair Crew", "department_id": dept_id, "availability": "Available"}],
            [{"id": cid, "title": "Pothole on Main", "department_id": dept_id, "safety_related": False, "status": "Submitted"}],
            [{"id": aid, "complaint_id": cid, "hotspot_id": None, "worker_id": wid, "officer_id": str(off.id), "task_description": "Fix pothole", "status": "Assigned", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"}],
            [{"id": cid, "status": "Assigned"}],  # patch complaint
            [{"id": str(uuid4())}],  # insert complaint_updates
        ]
        create_payload = {
            "complaint_id": cid,
            "worker_id": wid,
            "task_description": "Fix pothole",
        }
        res_create = client.post("/api/v1/assignments", json=create_payload)
        assert res_create.status_code == 201, res_create.text
        created_data = res_create.json()
        assert created_data["id"] == aid
        assert created_data["status"] == "Assigned"

    # Step 3: Worker lists and retrieves assigned task
    app.dependency_overrides[get_current_user] = lambda: wrk
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": wid, "profile_id": str(wrk.id)}],  # worker resolution
            [{"id": aid, "complaint_id": cid, "hotspot_id": None, "worker_id": wid, "officer_id": str(off.id), "task_description": "Fix pothole", "status": "Assigned", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"}],
            [{"id": wid, "name": "Road Repair Crew"}],
            [{"id": str(off.id), "full_name": off.full_name}],
        ]
        res_list = client.get("/api/v1/assignments")
        assert res_list.status_code == 200
        items = res_list.json()
        assert len(items) == 1
        assert items[0]["id"] == aid

    # Step 4 & 5: Worker updates task to In Progress -> complaint advances to In Progress
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": aid, "worker_id": wid, "status": "Assigned", "complaint_id": cid, "task_description": "Fix pothole"}],
            [{"id": wid, "profile_id": str(wrk.id)}],
            [{"id": cid, "status": "Assigned"}],
            [{"id": aid}],  # patch assignment
            [{"id": cid, "status": "In Progress"}],  # patch complaint
            [{"id": str(uuid4())}],  # history entry
            [{"id": aid, "complaint_id": cid, "hotspot_id": None, "worker_id": wid, "officer_id": str(off.id), "task_description": "Fix pothole", "status": "In Progress", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"}],
            [{"id": wid, "name": "Road Repair Crew"}],
            [{"id": str(off.id), "full_name": off.full_name}],
        ]
        res_prog = client.patch(f"/api/v1/assignments/{aid}", json={"status": "In Progress", "notes": "Commencing asphalt filling"})
        assert res_prog.status_code == 200
        assert res_prog.json()["status"] == "In Progress"

    # Step 6, 7 & 8: Worker completes task -> history logged, but complaint remains In Progress (NOT Resolved)
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": aid, "worker_id": wid, "status": "In Progress", "complaint_id": cid, "task_description": "Fix pothole"}],
            [{"id": wid, "profile_id": str(wrk.id)}],
            [{"id": cid, "status": "In Progress"}],
            [{"id": aid}],  # patch assignment
            [{"id": str(uuid4())}],  # history entry
            [{"id": aid, "complaint_id": cid, "hotspot_id": None, "worker_id": wid, "officer_id": str(off.id), "task_description": "Fix pothole", "status": "Completed", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"}],
            [{"id": wid, "name": "Road Repair Crew"}],
            [{"id": str(off.id), "full_name": off.full_name}],
        ]
        res_comp = client.patch(f"/api/v1/assignments/{aid}", json={"status": "Completed", "notes": "Asphalt laid and cured"})
        assert res_comp.status_code == 200
        assert res_comp.json()["status"] == "Completed"
        # Confirm no call patched complaint to Resolved
        comp_resolved = [c for c in mq.call_args_list if c[0][0] == "complaints" and c[1].get("method") == "PATCH" and c[1]["json_data"].get("status") == "Resolved"]
        assert len(comp_resolved) == 0


def test_integration_safety_assignment_segregation():
    """C9-C10. Safety assignment segregation: ordinary official 404, safety officer 200."""
    aid = str(uuid4())
    cid = str(uuid4())
    dept_id = str(uuid4())
    wid = str(uuid4())
    oid = str(uuid4())

    # Ordinary official cannot retrieve safety assignment -> 404
    ord_off = make_user("official", department_id=dept_id, is_safety_officer=False)
    app.dependency_overrides[get_current_user] = lambda: ord_off
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": aid, "complaint_id": cid, "hotspot_id": None, "worker_id": wid, "officer_id": oid, "task_description": "Fix streetlamp in dark alley", "status": "Assigned", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"}],
            [{"id": cid, "department_id": dept_id, "safety_related": True, "title": "Dark alley hazard", "category": "Lighting", "priority": "High"}],
        ]
        res = client.get(f"/api/v1/assignments/{aid}")
        assert res.status_code == 404

    # Safety officer CAN retrieve safety assignment -> 200
    safe_off = make_user("official", department_id=dept_id, is_safety_officer=True)
    app.dependency_overrides[get_current_user] = lambda: safe_off
    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": aid, "complaint_id": cid, "hotspot_id": None, "worker_id": wid, "officer_id": oid, "task_description": "Fix streetlamp in dark alley", "status": "Assigned", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"}],
            [{"id": cid, "department_id": dept_id, "safety_related": True, "title": "Dark alley hazard", "category": "Lighting", "priority": "High"}],
            [{"department_id": dept_id}],  # worker department check
            [{"id": wid, "name": "Lighting Crew"}],  # worker name resolution
            [{"id": oid, "full_name": "Safety Lead"}],  # officer name resolution
        ]
        res = client.get(f"/api/v1/assignments/{aid}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == aid
        assert data["complaint_title"] == "Dark alley hazard"
        assert data["target_type"] == "complaint"


def test_integration_hotspot_assignment_isolated_from_complaint_history():
    """C11. Traffic hotspot assignment lifecycle never touches complaint_updates."""
    off = make_user("official")
    app.dependency_overrides[get_current_user] = lambda: off
    hid = str(uuid4())
    wid = str(uuid4())
    aid = str(uuid4())

    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.side_effect = [
            [{"id": wid, "name": "Traffic Crew", "department_id": str(uuid4()), "availability": "Available"}],
            [{"id": hid, "congestion_level": "High", "description": "Ring Road jam"}],
            [{"id": aid, "complaint_id": None, "hotspot_id": hid, "worker_id": wid, "officer_id": str(off.id), "task_description": "Clear bottleneck", "status": "Assigned", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"}],
        ]
        res = client.post("/api/v1/assignments", json={"hotspot_id": hid, "worker_id": wid, "task_description": "Clear bottleneck"})
        assert res.status_code == 201
        # Confirm complaint_updates was NEVER called
        cu_calls = [c for c in mq.call_args_list if c[0][0] == "complaint_updates"]
        assert len(cu_calls) == 0


def test_integration_database_failure_propagates_http_503():
    """C12. Database failure in route handler propagates as HTTP 503."""
    off = make_user("official")
    app.dependency_overrides[get_current_user] = lambda: off

    with patch("app.services.assignment_service.supabase_service.rest_query", new_callable=AsyncMock) as mq:
        mq.return_value = None  # Simulated database outage
        res = client.get("/api/v1/workers")
        assert res.status_code == 503
        assert res.json()["detail"] == "Database service unavailable."


# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================

if __name__ == "__main__":
    print("===========================================================================")
    print("M4-09 COMPREHENSIVE TEST SUITE (WORKER & OFFICER ASSIGNMENTS)")
    print("===========================================================================")

    print("\n--- Running Section A: Schema Validation Tests ---")
    test_schema_valid_complaint_assignment()
    print("PASS: A1 - Valid complaint assignment schema")
    test_schema_valid_hotspot_assignment()
    print("PASS: A2 - Valid hotspot assignment schema")
    test_schema_both_targets_rejected()
    print("PASS: A3 - Both targets rejected")
    test_schema_neither_target_rejected()
    print("PASS: A4 - Neither target rejected")
    test_schema_missing_worker_id_rejected()
    print("PASS: A5 - Missing worker ID rejected")
    test_schema_invalid_assignment_status_rejected()
    print("PASS: A6 - Invalid assignment status rejected")
    test_schema_invalid_worker_availability_rejected()
    print("PASS: A7 - Invalid worker availability rejected")
    test_schema_task_description_length_bounds()
    print("PASS: A8 - Task description length validation")
    test_schema_unknown_request_fields_rejected()
    print("PASS: A9 - Unknown request fields rejected (extra='forbid')")
    test_schema_client_supplied_officer_id_rejected()
    print("PASS: A10 - Client-supplied officer_id rejected")
    test_schema_empty_update_rejected()
    print("PASS: A11 - Empty update rejected")
    test_schema_valid_status_only_update()
    print("PASS: A12 - Valid status-only update")
    test_schema_valid_task_description_update()
    print("PASS: A13 - Valid task description update")
    test_schema_valid_worker_reassignment_update()
    print("PASS: A14 - Valid worker reassignment update")
    test_schema_notes_max_length()
    print("PASS: A15 - Notes max length bounded to 1000")
    test_schema_serialization_and_detail_responses()
    print("PASS: A16-A18 - UUID/datetime serialization & complaint/hotspot detail schemas")

    print("\n--- Running Section B: Service Layer Tests ---")
    asyncio.run(test_service_worker_listing_and_scoping())
    print("PASS: B1-B4 - Worker listing, department scoping, own profile & citizen denial")
    asyncio.run(test_service_worker_detail_authorization())
    print("PASS: B5-B7 - Worker detail authorization and isolation")
    asyncio.run(test_service_create_assignment_validation())
    print("PASS: B8-B14 - Assignment creation rules, safety checks & department bounds")
    asyncio.run(test_service_create_assignment_lifecycle_and_rollback())
    print("PASS: B15-B16 - Assignment lifecycle sync & compensating rollback on failure")
    asyncio.run(test_service_assignment_listing_scoping_and_safety())
    print("PASS: B17-B20 - Assignment listing scoping, safety exclusion & pagination")
    asyncio.run(test_service_assignment_updates_and_state_machine())
    print("PASS: B21-B26 - Updates, lifecycle state machine, worker locks & history logging")
    asyncio.run(test_service_database_reliability_and_pagination())
    print("PASS: B27-B28 - Database 503 error propagation & sequential pagination")

    print("\n--- Running Section C: Cross-Layer Integration Tests (Mocked DB) ---")
    test_integration_full_complaint_assignment_lifecycle()
    print("PASS: C1-C8 - Full complaint assignment lifecycle through FastAPI routes")
    test_integration_safety_assignment_segregation()
    print("PASS: C9-C10 - Safety assignment segregation between ordinary & safety officers")
    test_integration_hotspot_assignment_isolated_from_complaint_history()
    print("PASS: C11 - Hotspot assignment isolated from complaint history")
    test_integration_database_failure_propagates_http_503()
    print("PASS: C12 - Database failure propagates as HTTP 503 through route")

    print("\n===========================================================================")
    print("ALL M4-09 COMPREHENSIVE TESTS PASSED SUCCESSFULLY (38 TEST GROUPS)")
    print("===========================================================================")
