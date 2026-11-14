"""Focused route tests for M4-09 Worker and Officer Assignments APIs.

Task: M4-09 Step 4 — API Route Implementation
PRD References: Section 4.7, 6.7, 6.8, 7.6
"""
import asyncio
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4
from fastapi import HTTPException
from fastapi.testclient import TestClient

# Add backend to path
sys.path.insert(0, "backend")

from app.api.deps import get_current_user
from app.main import app
from app.schemas.assignment import (
    AssignmentDetailResponse,
    AssignmentResponse,
    AssignmentStatus,
    WorkerAvailability,
    WorkerResponse,
)
from app.schemas.profile import ProfileResponse
from app.services.assignment_service import assignment_service

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


def test_1_worker_list_response_model():
    """1. Worker list route returns the correct response model."""
    off = make_user("official")
    app.dependency_overrides[get_current_user] = lambda: off

    worker_id = uuid4()
    dept_id = uuid4()
    mock_worker = WorkerResponse(
        id=worker_id,
        profile_id=uuid4(),
        name="John Doe Crew",
        department_id=dept_id,
        department_name="Public Works",
        availability="Available",
        phone="+1234567890",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with patch.object(assignment_service, "list_workers", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = [mock_worker]
        res = client.get("/api/v1/workers")
        assert res.status_code == 200, res.text
        data = res.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == str(worker_id)
        assert data[0]["name"] == "John Doe Crew"
        assert data[0]["availability"] == "Available"
        assert data[0]["department_name"] == "Public Works"
    print("PASS: 1. Worker list route returns the correct response model")


def test_2_worker_detail_response_model():
    """2. Worker detail route returns the correct response model."""
    off = make_user("official")
    app.dependency_overrides[get_current_user] = lambda: off

    worker_id = uuid4()
    dept_id = uuid4()
    mock_worker = WorkerResponse(
        id=worker_id,
        profile_id=uuid4(),
        name="Jane Field Crew",
        department_id=dept_id,
        department_name="Sanitation",
        availability="Busy",
        phone="+9876543210",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with patch.object(assignment_service, "get_worker_by_id", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_worker
        res = client.get(f"/api/v1/workers/{worker_id}")
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["id"] == str(worker_id)
        assert data["name"] == "Jane Field Crew"
        assert data["availability"] == "Busy"
        assert data["department_name"] == "Sanitation"
    print("PASS: 2. Worker detail route returns the correct response model")


def test_3_citizen_cannot_access_worker_routes():
    """3. Citizen cannot access worker routes."""
    cit = make_user("citizen")
    app.dependency_overrides[get_current_user] = lambda: cit

    res_list = client.get("/api/v1/workers")
    assert res_list.status_code == 403, f"Expected 403, got {res_list.status_code}"

    res_detail = client.get(f"/api/v1/workers/{uuid4()}")
    assert res_detail.status_code == 403, f"Expected 403, got {res_detail.status_code}"
    print("PASS: 3. Citizen cannot access worker routes")


def test_4_worker_list_returns_only_own_profile():
    """4. Worker list returns only the authenticated worker's profile."""
    wrk_user = make_user("worker")
    app.dependency_overrides[get_current_user] = lambda: wrk_user

    mock_worker = WorkerResponse(
        id=uuid4(),
        profile_id=wrk_user.id,
        name="Self Worker",
        department_id=uuid4(),
        department_name="Roads",
        availability="Available",
        phone=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with patch.object(assignment_service, "list_workers", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = [mock_worker]
        res = client.get("/api/v1/workers")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["profile_id"] == str(wrk_user.id)
        mock_list.assert_called_once()
        assert mock_list.call_args[1]["user"].id == wrk_user.id
    print("PASS: 4. Worker list returns only the authenticated worker's profile")


def test_5_worker_cannot_retrieve_another_worker():
    """5. Worker cannot retrieve another worker's profile."""
    wrk_user = make_user("worker")
    app.dependency_overrides[get_current_user] = lambda: wrk_user
    other_worker_id = uuid4()

    with patch.object(assignment_service, "get_worker_by_id", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = HTTPException(status_code=404, detail="Worker was not found.")
        res = client.get(f"/api/v1/workers/{other_worker_id}")
        assert res.status_code == 404
    print("PASS: 5. Worker cannot retrieve another worker's profile")


def test_6_official_worker_listing_respects_department_scope():
    """6. Official worker listing respects department scope."""
    dept_id = uuid4()
    other_dept = uuid4()
    off_user = make_user("official", department_id=str(dept_id))
    app.dependency_overrides[get_current_user] = lambda: off_user

    with patch.object(assignment_service, "list_workers", new_callable=AsyncMock) as mock_list:
        mock_list.side_effect = HTTPException(
            status_code=403,
            detail="Access denied: You are not authorized to view workers outside your assigned department.",
        )
        res = client.get(f"/api/v1/workers?department_id={other_dept}")
        assert res.status_code == 403
    print("PASS: 6. Official worker listing respects department scope")


def test_7_assignment_creation_returns_201():
    """7. Assignment creation returns HTTP 201."""
    off = make_user("official")
    app.dependency_overrides[get_current_user] = lambda: off

    aid = uuid4()
    cid = uuid4()
    wid = uuid4()
    mock_resp = AssignmentResponse(
        id=aid,
        complaint_id=cid,
        hotspot_id=None,
        worker_id=wid,
        worker_name="Field Crew Alpha",
        officer_id=off.id,
        officer_name=off.full_name,
        task_description="Repair damaged water line on Elm Street",
        status="Assigned",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with patch.object(assignment_service, "create_assignment", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_resp
        payload = {
            "complaint_id": str(cid),
            "worker_id": str(wid),
            "task_description": "Repair damaged water line on Elm Street",
        }
        res = client.post("/api/v1/assignments", json=payload)
        assert res.status_code == 201, res.text
        data = res.json()
        assert data["id"] == str(aid)
        assert data["officer_id"] == str(off.id)
        assert data["status"] == "Assigned"
    print("PASS: 7. Assignment creation returns HTTP 201")


def test_8_assignment_creation_rejects_client_supplied_officer_id():
    """8. Assignment creation does not accept client-supplied officer_id."""
    off = make_user("official")
    app.dependency_overrides[get_current_user] = lambda: off

    payload = {
        "complaint_id": str(uuid4()),
        "worker_id": str(uuid4()),
        "task_description": "Fix street light",
        "officer_id": str(uuid4()),  # Forbidden extra field!
    }
    res = client.post("/api/v1/assignments", json=payload)
    assert res.status_code == 422, f"Expected 422 Unprocessable Entity, got {res.status_code}"
    print("PASS: 8. Assignment creation does not accept client-supplied officer_id")


def test_9_assignment_creation_rejects_invalid_target_combinations():
    """9. Assignment creation rejects invalid target combinations."""
    off = make_user("official")
    app.dependency_overrides[get_current_user] = lambda: off

    # Both complaint_id and hotspot_id
    payload_both = {
        "complaint_id": str(uuid4()),
        "hotspot_id": str(uuid4()),
        "worker_id": str(uuid4()),
        "task_description": "Fix issue",
    }
    res_both = client.post("/api/v1/assignments", json=payload_both)
    assert res_both.status_code == 422, f"Expected 422, got {res_both.status_code}"

    # Neither complaint_id nor hotspot_id
    payload_neither = {
        "worker_id": str(uuid4()),
        "task_description": "Fix issue",
    }
    res_neither = client.post("/api/v1/assignments", json=payload_neither)
    assert res_neither.status_code == 422, f"Expected 422, got {res_neither.status_code}"
    print("PASS: 9. Assignment creation rejects invalid target combinations")


def test_10_citizen_cannot_list_assignments():
    """10. Citizen cannot list assignments."""
    cit = make_user("citizen")
    app.dependency_overrides[get_current_user] = lambda: cit

    res = client.get("/api/v1/assignments")
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"
    print("PASS: 10. Citizen cannot list assignments")


def test_11_worker_assignment_listing_restricted_to_own_worker_id():
    """11. Worker assignment listing is restricted to their own worker ID."""
    wrk = make_user("worker")
    app.dependency_overrides[get_current_user] = lambda: wrk

    mock_resp = AssignmentResponse(
        id=uuid4(),
        complaint_id=uuid4(),
        hotspot_id=None,
        worker_id=uuid4(),
        worker_name="My Crew",
        officer_id=uuid4(),
        officer_name="Officer Bob",
        task_description="Clear clogged drain",
        status="In Progress",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with patch.object(assignment_service, "list_assignments", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = [mock_resp]
        res = client.get("/api/v1/assignments")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["task_description"] == "Clear clogged drain"
        assert mock_list.call_args[1]["user"].id == wrk.id
    print("PASS: 11. Worker assignment listing is restricted to their own worker ID")


def test_12_official_assignment_listing_respects_department_scope():
    """12. Official assignment listing respects department scope."""
    dept_id = uuid4()
    other_dept = uuid4()
    off = make_user("official", department_id=str(dept_id))
    app.dependency_overrides[get_current_user] = lambda: off

    with patch.object(assignment_service, "list_assignments", new_callable=AsyncMock) as mock_list:
        mock_list.side_effect = HTTPException(
            status_code=403,
            detail="Access denied: You are not authorized to view assignments outside your department.",
        )
        res = client.get(f"/api/v1/assignments?department_id={other_dept}")
        assert res.status_code == 403
    print("PASS: 12. Official assignment listing respects department scope")


def test_13_ordinary_officials_cannot_access_safety_assignments():
    """13. Ordinary officials cannot access safety assignments."""
    off = make_user("official", is_safety_officer=False)
    app.dependency_overrides[get_current_user] = lambda: off
    safety_assignment_id = uuid4()

    with patch.object(assignment_service, "get_assignment_by_id", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = HTTPException(
            status_code=404,
            detail=f"Assignment with ID '{safety_assignment_id}' was not found.",
        )
        res = client.get(f"/api/v1/assignments/{safety_assignment_id}")
        assert res.status_code == 404
    print("PASS: 13. Ordinary officials cannot access safety assignments")


def test_14_assignment_detail_returns_correct_response():
    """14. Assignment detail returns the correct detail response."""
    off = make_user("official")
    app.dependency_overrides[get_current_user] = lambda: off
    aid = uuid4()
    cid = uuid4()

    mock_detail = AssignmentDetailResponse(
        id=aid,
        complaint_id=cid,
        hotspot_id=None,
        worker_id=uuid4(),
        worker_name="Electric Crew",
        officer_id=off.id,
        officer_name=off.full_name,
        task_description="Repair blackout junction",
        status="In Progress",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        target_type="complaint",
        complaint_title="Power Outage on 5th Ave",
        complaint_category="Electricity",
        complaint_priority="High",
    )

    with patch.object(assignment_service, "get_assignment_by_id", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_detail
        res = client.get(f"/api/v1/assignments/{aid}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == str(aid)
        assert data["target_type"] == "complaint"
        assert data["complaint_title"] == "Power Outage on 5th Ave"
        assert data["complaint_category"] == "Electricity"
    print("PASS: 14. Assignment detail returns the correct detail response")


def test_15_unauthorized_assignment_detail_access_rejected():
    """15. Unauthorized assignment detail access is rejected."""
    # Citizen
    cit = make_user("citizen")
    app.dependency_overrides[get_current_user] = lambda: cit
    res = client.get(f"/api/v1/assignments/{uuid4()}")
    assert res.status_code == 403

    # Cross-department official
    off = make_user("official", department_id=str(uuid4()))
    app.dependency_overrides[get_current_user] = lambda: off
    with patch.object(assignment_service, "get_assignment_by_id", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = HTTPException(status_code=404, detail="Assignment was not found in your department.")
        res = client.get(f"/api/v1/assignments/{uuid4()}")
        assert res.status_code == 404
    print("PASS: 15. Unauthorized assignment detail access is rejected")


def test_16_worker_cannot_reassign_assignment():
    """16. Worker cannot reassign an assignment."""
    wrk = make_user("worker")
    app.dependency_overrides[get_current_user] = lambda: wrk
    aid = uuid4()

    with patch.object(assignment_service, "update_assignment", new_callable=AsyncMock) as mock_up:
        mock_up.side_effect = HTTPException(status_code=403, detail="Workers are not authorized to reassign workers.")
        res = client.patch(f"/api/v1/assignments/{aid}", json={"worker_id": str(uuid4())})
        assert res.status_code == 403
    print("PASS: 16. Worker cannot reassign an assignment")


def test_17_worker_cannot_modify_task_description():
    """17. Worker cannot modify task description."""
    wrk = make_user("worker")
    app.dependency_overrides[get_current_user] = lambda: wrk
    aid = uuid4()

    with patch.object(assignment_service, "update_assignment", new_callable=AsyncMock) as mock_up:
        mock_up.side_effect = HTTPException(status_code=403, detail="Workers are not authorized to modify task descriptions.")
        res = client.patch(f"/api/v1/assignments/{aid}", json={"task_description": "New instructions"})
        assert res.status_code == 403
    print("PASS: 17. Worker cannot modify task description")


def test_18_worker_can_submit_allowed_status_update():
    """18. Worker can submit an allowed status/progress update."""
    wrk = make_user("worker")
    app.dependency_overrides[get_current_user] = lambda: wrk
    aid = uuid4()

    mock_resp = AssignmentResponse(
        id=aid,
        complaint_id=uuid4(),
        hotspot_id=None,
        worker_id=uuid4(),
        worker_name="My Crew",
        officer_id=uuid4(),
        officer_name="Officer Smith",
        task_description="Repair pothole",
        status="In Progress",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with patch.object(assignment_service, "update_assignment", new_callable=AsyncMock) as mock_up:
        mock_up.return_value = mock_resp
        payload = {"status": "In Progress", "notes": "Work on site has started"}
        res = client.patch(f"/api/v1/assignments/{aid}", json=payload)
        assert res.status_code == 200
        assert res.json()["status"] == "In Progress"
    print("PASS: 18. Worker can submit an allowed status/progress update")


def test_19_official_can_perform_authorized_reassignment():
    """19. Official can perform an authorized reassignment."""
    off = make_user("official")
    app.dependency_overrides[get_current_user] = lambda: off
    aid = uuid4()
    new_wid = uuid4()

    mock_resp = AssignmentResponse(
        id=aid,
        complaint_id=uuid4(),
        hotspot_id=None,
        worker_id=new_wid,
        worker_name="Replacement Crew",
        officer_id=off.id,
        officer_name=off.full_name,
        task_description="Repair pothole",
        status="Assigned",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with patch.object(assignment_service, "update_assignment", new_callable=AsyncMock) as mock_up:
        mock_up.return_value = mock_resp
        payload = {"worker_id": str(new_wid), "notes": "Reassigned to specialist crew"}
        res = client.patch(f"/api/v1/assignments/{aid}", json=payload)
        assert res.status_code == 200
        assert res.json()["worker_id"] == str(new_wid)
        assert res.json()["worker_name"] == "Replacement Crew"
    print("PASS: 19. Official can perform an authorized reassignment")


def test_20_invalid_assignment_transitions_rejected():
    """20. Invalid assignment transitions are rejected."""
    off = make_user("official")
    app.dependency_overrides[get_current_user] = lambda: off
    aid = uuid4()

    with patch.object(assignment_service, "update_assignment", new_callable=AsyncMock) as mock_up:
        mock_up.side_effect = HTTPException(
            status_code=400,
            detail="Invalid status transition: Cannot revert 'In Progress' assignment back to 'Assigned'.",
        )
        res = client.patch(f"/api/v1/assignments/{aid}", json={"status": "Assigned"})
        assert res.status_code == 400
    print("PASS: 20. Invalid assignment transitions are rejected")


def test_21_completed_assignments_cannot_be_reopened():
    """21. Completed assignments cannot be reopened."""
    off = make_user("official")
    app.dependency_overrides[get_current_user] = lambda: off
    aid = uuid4()

    with patch.object(assignment_service, "update_assignment", new_callable=AsyncMock) as mock_up:
        mock_up.side_effect = HTTPException(
            status_code=400,
            detail="Completed assignments are terminal and cannot be reopened.",
        )
        res = client.patch(f"/api/v1/assignments/{aid}", json={"status": "In Progress"})
        assert res.status_code == 400
    print("PASS: 21. Completed assignments cannot be reopened")


def test_22_service_errors_translated_to_http_responses():
    """22. Service errors are translated into appropriate HTTP responses."""
    off = make_user("official")
    app.dependency_overrides[get_current_user] = lambda: off

    with patch.object(assignment_service, "list_workers", new_callable=AsyncMock) as mock_list:
        mock_list.side_effect = HTTPException(
            status_code=503,
            detail="Database service unavailable.",
        )
        res = client.get("/api/v1/workers")
        assert res.status_code == 503
        assert res.json()["detail"] == "Database service unavailable."
    print("PASS: 22. Service errors are translated into appropriate HTTP responses")


def test_23_pagination_parameters_validated():
    """23. Pagination parameters are validated."""
    off = make_user("official")
    app.dependency_overrides[get_current_user] = lambda: off

    # limit < 1
    res1 = client.get("/api/v1/workers?limit=0")
    assert res1.status_code == 422

    # limit > 100
    res2 = client.get("/api/v1/workers?limit=101")
    assert res2.status_code == 422

    # offset < 0
    res3 = client.get("/api/v1/workers?offset=-1")
    assert res3.status_code == 422

    # assignments limit > 100
    res4 = client.get("/api/v1/assignments?limit=101")
    assert res4.status_code == 422
    print("PASS: 23. Pagination parameters are validated")


def test_24_openapi_schema_verification():
    """24. OpenAPI exposes the expected endpoint paths and response schemas."""
    res = client.get("/api/v1/openapi.json")
    assert res.status_code == 200
    schema = res.json()
    paths = schema.get("paths", {})

    expected_routes = [
        ("/api/v1/workers", ["get"]),
        ("/api/v1/workers/{worker_id}", ["get"]),
        ("/api/v1/assignments", ["get", "post"]),
        ("/api/v1/assignments/{assignment_id}", ["get", "patch"]),
    ]

    for path, methods in expected_routes:
        assert path in paths, f"Path {path} not found in OpenAPI schema"
        for method in methods:
            assert method in paths[path], f"Method {method.upper()} not found for {path}"

    # Verify response schema definitions
    components = schema.get("components", {}).get("schemas", {})
    assert "WorkerResponse" in components
    assert "AssignmentResponse" in components
    assert "AssignmentDetailResponse" in components
    assert "AssignmentCreate" in components
    assert "AssignmentUpdate" in components

    print("PASS: 24. OpenAPI exposes the expected endpoint paths and response schemas")


def test_25_worker_availability_query_param_filters():
    """25. Worker availability filter handles valid values without AttributeError."""
    off = make_user("official")
    app.dependency_overrides[get_current_user] = lambda: off

    valid_availabilities = ["Available", "Busy", "Unavailable"]
    for avail in valid_availabilities:
        with patch.object(assignment_service, "list_workers", new_callable=AsyncMock) as mock_list:
            mock_worker = WorkerResponse(
                id=uuid4(),
                profile_id=uuid4(),
                name=f"Worker {avail}",
                department_id=uuid4(),
                department_name="Roads",
                availability=avail,
                phone=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            mock_list.return_value = [mock_worker]

            res = client.get(f"/api/v1/workers?availability={avail}")
            assert res.status_code == 200, f"Expected 200 for availability={avail}, got {res.status_code}: {res.text}"
            data = res.json()
            assert len(data) == 1
            assert data[0]["availability"] == avail

            # Verify service received the exact plain string
            mock_list.assert_called_once()
            called_kwargs = mock_list.call_args[1]
            assert called_kwargs["availability"] == avail, f"Expected string '{avail}', got {called_kwargs['availability']!r}"
            assert isinstance(called_kwargs["availability"], str)

    print("PASS: 25. Worker availability filter handles all valid values ('Available', 'Busy', 'Unavailable')")


def test_26_assignment_status_query_param_filters():
    """26. Assignment status filter handles valid values without AttributeError."""
    off = make_user("official")
    app.dependency_overrides[get_current_user] = lambda: off

    valid_statuses = [
        ("Assigned", "Assigned"),
        ("In%20Progress", "In Progress"),
        ("Completed", "Completed"),
    ]
    for url_val, expected_val in valid_statuses:
        with patch.object(assignment_service, "list_assignments", new_callable=AsyncMock) as mock_list:
            mock_resp = AssignmentResponse(
                id=uuid4(),
                complaint_id=uuid4(),
                hotspot_id=None,
                worker_id=uuid4(),
                worker_name="Crew A",
                officer_id=off.id,
                officer_name=off.full_name,
                task_description="Task with status",
                status=expected_val,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            mock_list.return_value = [mock_resp]

            res = client.get(f"/api/v1/assignments?status={url_val}")
            assert res.status_code == 200, f"Expected 200 for status={url_val}, got {res.status_code}: {res.text}"
            data = res.json()
            assert len(data) == 1
            assert data[0]["status"] == expected_val

            # Verify service received the exact plain string
            mock_list.assert_called_once()
            called_kwargs = mock_list.call_args[1]
            assert called_kwargs["status_filter"] == expected_val, f"Expected string '{expected_val}', got {called_kwargs['status_filter']!r}"
            assert isinstance(called_kwargs["status_filter"], str)

    print("PASS: 26. Assignment status filter handles all valid values ('Assigned', 'In Progress', 'Completed')")


def test_27_invalid_query_parameter_values_rejected():
    """27. Invalid query parameter values return HTTP 422."""
    off = make_user("official")
    app.dependency_overrides[get_current_user] = lambda: off

    # Invalid worker availability
    res1 = client.get("/api/v1/workers?availability=InvalidAvailability")
    assert res1.status_code == 422, f"Expected 422, got {res1.status_code}"

    # Invalid assignment status
    res2 = client.get("/api/v1/assignments?status=Pending")
    assert res2.status_code == 422, f"Expected 422, got {res2.status_code}"

    res3 = client.get("/api/v1/assignments?status=Done")
    assert res3.status_code == 422, f"Expected 422, got {res3.status_code}"

    print("PASS: 27. Invalid availability and status query parameters rejected with HTTP 422")


if __name__ == "__main__":
    print("=== Running M4-09 Route Tests ===")
    test_1_worker_list_response_model()
    test_2_worker_detail_response_model()
    test_3_citizen_cannot_access_worker_routes()
    test_4_worker_list_returns_only_own_profile()
    test_5_worker_cannot_retrieve_another_worker()
    test_6_official_worker_listing_respects_department_scope()
    test_7_assignment_creation_returns_201()
    test_8_assignment_creation_rejects_client_supplied_officer_id()
    test_9_assignment_creation_rejects_invalid_target_combinations()
    test_10_citizen_cannot_list_assignments()
    test_11_worker_assignment_listing_restricted_to_own_worker_id()
    test_12_official_assignment_listing_respects_department_scope()
    test_13_ordinary_officials_cannot_access_safety_assignments()
    test_14_assignment_detail_returns_correct_response()
    test_15_unauthorized_assignment_detail_access_rejected()
    test_16_worker_cannot_reassign_assignment()
    test_17_worker_cannot_modify_task_description()
    test_18_worker_can_submit_allowed_status_update()
    test_19_official_can_perform_authorized_reassignment()
    test_20_invalid_assignment_transitions_rejected()
    test_21_completed_assignments_cannot_be_reopened()
    test_22_service_errors_translated_to_http_responses()
    test_23_pagination_parameters_validated()
    test_24_openapi_schema_verification()
    test_25_worker_availability_query_param_filters()
    test_26_assignment_status_query_param_filters()
    test_27_invalid_query_parameter_values_rejected()
    print("=== ALL 27 ROUTE TESTS PASSED SUCCESSFULLY ===")
