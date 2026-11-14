"""Comprehensive Test Suite for M4-07 Safety Report Handling.

Covers all 25 criteria specified in Task M4-07:
1. Citizen can submit a safety report.
2. safety_related is forced to true.
3. citizen_id is derived from authentication.
4. Citizen cannot inject privileged fields.
5. Citizen can retrieve their own reports.
6. /mine and /my return equivalent authorized results.
7. Citizen cannot access another citizen's report.
8. Ordinary officials cannot access the safety register.
9. Workers cannot access the safety register.
10. Designated safety officer can list reports.
11. Department-scoped safety officer cannot access another department's report.
12. City-wide safety officer can access authorized municipal reports.
13. Safety officer can retrieve individual report details.
14. Citizen cannot retrieve another report's details.
15. Safety officer can update investigation status.
16. Invalid status transitions are rejected.
17. History insertion failure triggers appropriate rollback.
18. Image paths belonging to another user are rejected.
19. Unauthorized image access is rejected.
20. Signed URLs are generated only after authorization.
21. Citizen cannot change priority or department through the submission payload.
22. Query parameters cannot expand access.
23. Complaint history is returned in correct order.
24. Existing M4-04 complaint lifecycle behavior remains intact.
25. M4-06 safety-zone and map behavior remains intact.
"""
import asyncio
import functools
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

# Ensure unbuffered output
print = functools.partial(print, flush=True)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from fastapi import HTTPException
import httpx
from pydantic import ValidationError

from app.api.deps import get_current_user, require_role, require_safety_officer
from app.main import app
from app.schemas.ai import AIAnalysisResponse
from app.schemas.complaint import ComplaintCreate, ComplaintResponse
from app.schemas.profile import ProfileResponse
from app.schemas.safety import (
    ALLOWED_SAFETY_CATEGORIES,
    SafetyInvestigationUpdate,
    SafetyReportCreate,
    SafetyReportDetailResponse,
    SafetyReportResponse,
)
from app.services.complaint_service import complaint_service
from app.services.map_service import map_service
from app.services.safety_service import SafetyService, safety_service
from app.services.storage_service import storage_service

# Test UUIDs
DEPT_PWD = UUID("11111111-1111-1111-1111-111111111111")
DEPT_LIGHTING = UUID("44444444-4444-4444-4444-444444444444")
DEPT_OTHER = UUID("22222222-2222-2222-2222-222222222222")

CITIZEN_1 = ProfileResponse(
    id=uuid4(),
    full_name="Alice Citizen",
    role="citizen",
    department_id=None,
    is_safety_officer=False,
)

CITIZEN_2 = ProfileResponse(
    id=uuid4(),
    full_name="Bob Citizen",
    role="citizen",
    department_id=None,
    is_safety_officer=False,
)

SAFETY_OFFICER_PWD = ProfileResponse(
    id=uuid4(),
    full_name="Officer Charlie (PWD Safety)",
    role="official",
    department_id=DEPT_PWD,
    is_safety_officer=True,
)

SAFETY_OFFICER_CITYWIDE = ProfileResponse(
    id=uuid4(),
    full_name="Officer Diana (Citywide Safety)",
    role="official",
    department_id=None,
    is_safety_officer=True,
)

ORDINARY_OFFICIAL = ProfileResponse(
    id=uuid4(),
    full_name="Officer Eve (Ordinary Official)",
    role="official",
    department_id=DEPT_PWD,
    is_safety_officer=False,
)

WORKER_USER = ProfileResponse(
    id=uuid4(),
    full_name="Frank Worker",
    role="worker",
    department_id=DEPT_PWD,
    is_safety_officer=False,
)


def mock_ai_response():
    return AIAnalysisResponse(
        suggested_title="Dark Pedestrian Pathway Near Market",
        category="Unsafe public infrastructure",
        issue_type="Poor Lighting",
        department="Public Works Department",
        severity=7,
        summary="Non-functional streetlights causing unsafe conditions along pedestrian route.",
        recommended_action="Inspect lighting fixtures and replace faulty bulbs.",
        language="English",
        is_safety_related=True,
        safety_category="Lighting issue",
        needs_human_review=False,
    )


async def run_all_tests():
    passed = 0
    failed = 0
    total = 25

    print("\n" + "=" * 70)
    print("STARTING M4-07 SAFETY REPORT HANDLING TEST SUITE (25 TESTS)")
    print("=" * 70 + "\n")

    # -------------------------------------------------------------------------
    # Test 1: Citizen can submit a safety report
    # -------------------------------------------------------------------------
    try:
        report_data = SafetyReportCreate(
            title="Broken Streetlight on Central Ave",
            description="All lights on Central Ave between 4th and 5th street are out.",
            latitude=15.498,
            longitude=73.827,
            safety_category="Poor Lighting",
        )

        mock_created_record = {
            "id": str(uuid4()),
            "citizen_id": str(CITIZEN_1.id),
            "title": "Broken Streetlight on Central Ave",
            "description": report_data.description,
            "latitude": 15.498,
            "longitude": 73.827,
            "category": "Unsafe public infrastructure",
            "issue_type": "Poor Lighting",
            "department_id": str(DEPT_PWD),
            "image_url": None,
            "safety_related": True,
            "safety_category": "Poor Lighting",
            "status": "Submitted",
            "priority": "High",
            "severity": 7,
            "report_count": 1,
            "ai_summary": "Non-functional streetlights causing unsafe conditions.",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        with patch("app.services.safety_service.ai_service.analyze_complaint", AsyncMock(return_value=mock_ai_response())), \
             patch("app.services.safety_service.supabase_service.rest_query") as mock_rq:

            async def fake_rest(table, method="GET", params=None, json_data=None):
                if table == "departments" and method == "GET":
                    return [{"id": str(DEPT_PWD), "name": "Public Works Department"}]
                if table == "complaints" and method == "POST":
                    return [mock_created_record]
                if table == "complaint_updates" and method == "POST":
                    return [{"id": str(uuid4())}]
                return []

            mock_rq.side_effect = fake_rest

            result = await safety_service.create_safety_report(CITIZEN_1, report_data)
            assert result.id == UUID(mock_created_record["id"])
            assert result.status == "Submitted"
            assert result.safety_related is True
            assert result.safety_category == "Poor Lighting"
            assert result.citizen_id == CITIZEN_1.id

        passed += 1
        print("PASS - Test 1: Citizen can submit a safety report")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 1: {e}")

    # -------------------------------------------------------------------------
    # Test 2: safety_related is forced to true server-side
    # -------------------------------------------------------------------------
    try:
        report_data = SafetyReportCreate(
            description="Dark alleyway with broken fixtures near school.",
            latitude=15.501,
            longitude=73.830,
            safety_category="Lighting issue",
        )

        with patch("app.services.safety_service.ai_service.analyze_complaint", AsyncMock(return_value=mock_ai_response())), \
             patch("app.services.safety_service.supabase_service.rest_query") as mock_rq:

            captured_payload = {}

            async def fake_rest(table, method="GET", params=None, json_data=None):
                nonlocal captured_payload
                if table == "complaints" and method == "POST":
                    captured_payload = json_data
                    rec = dict(mock_created_record)
                    rec["safety_related"] = json_data.get("safety_related")
                    return [rec]
                if table == "complaint_updates" and method == "POST":
                    return [{"id": str(uuid4())}]
                if table == "departments":
                    return [{"id": str(DEPT_PWD), "name": "Public Works Department"}]
                return []

            mock_rq.side_effect = fake_rest

            result = await safety_service.create_safety_report(CITIZEN_1, report_data)
            assert captured_payload.get("safety_related") is True, "Database payload must force safety_related=True"
            assert result.safety_related is True

        passed += 1
        print("PASS - Test 2: safety_related is forced to true server-side")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 2: {e}")

    # -------------------------------------------------------------------------
    # Test 3: citizen_id is derived from authentication
    # -------------------------------------------------------------------------
    try:
        report_data = SafetyReportCreate(
            description="Deserted transit bus stop with broken glass.",
            latitude=15.495,
            longitude=73.820,
            safety_category="Deserted Bus Stop",
        )

        with patch("app.services.safety_service.ai_service.analyze_complaint", AsyncMock(return_value=mock_ai_response())), \
             patch("app.services.safety_service.supabase_service.rest_query") as mock_rq:

            captured_citizen_id = None

            async def fake_rest(table, method="GET", params=None, json_data=None):
                nonlocal captured_citizen_id
                if table == "complaints" and method == "POST":
                    captured_citizen_id = json_data.get("citizen_id")
                    rec = dict(mock_created_record)
                    rec["citizen_id"] = str(CITIZEN_1.id)
                    return [rec]
                if table == "complaint_updates" and method == "POST":
                    return [{"id": str(uuid4())}]
                if table == "departments":
                    return [{"id": str(DEPT_PWD), "name": "Public Works Department"}]
                return []

            mock_rq.side_effect = fake_rest

            result = await safety_service.create_safety_report(CITIZEN_1, report_data)
            assert captured_citizen_id == str(CITIZEN_1.id), "citizen_id must come from authenticated ProfileResponse"
            assert result.citizen_id == CITIZEN_1.id

        passed += 1
        print("PASS - Test 3: citizen_id is derived from authentication")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 3: {e}")

    # -------------------------------------------------------------------------
    # Test 4: Citizen cannot inject privileged fields
    # -------------------------------------------------------------------------
    try:
        rejected_attempts = 0
        privileged_payloads = [
            {"description": "Valid description test", "latitude": 15.4, "longitude": 73.8, "safety_category": "Poor Lighting", "citizen_id": str(uuid4())},
            {"description": "Valid description test", "latitude": 15.4, "longitude": 73.8, "safety_category": "Poor Lighting", "status": "Resolved"},
            {"description": "Valid description test", "latitude": 15.4, "longitude": 73.8, "safety_category": "Poor Lighting", "safety_related": False},
            {"description": "Valid description test", "latitude": 15.4, "longitude": 73.8, "safety_category": "Poor Lighting", "report_count": 10},
        ]

        for p in privileged_payloads:
            try:
                SafetyReportCreate(**p)
            except ValidationError:
                rejected_attempts += 1

        assert rejected_attempts == len(privileged_payloads), f"Expected {len(privileged_payloads)} validation errors, got {rejected_attempts}"
        passed += 1
        print("PASS - Test 4: Citizen cannot inject privileged fields (rejected via extra='forbid')")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 4: {e}")

    # -------------------------------------------------------------------------
    # Test 5: Citizen can retrieve their own reports
    # -------------------------------------------------------------------------
    try:
        mock_reports = [
            {
                "id": str(uuid4()),
                "citizen_id": str(CITIZEN_1.id),
                "title": "Dark Street 1",
                "description": "Pedestrian route unlit",
                "latitude": 15.49,
                "longitude": 73.82,
                "category": "Unsafe public infrastructure",
                "issue_type": "Poor Lighting",
                "department_id": str(DEPT_PWD),
                "image_url": None,
                "safety_related": True,
                "safety_category": "Poor Lighting",
                "status": "Submitted",
                "priority": "Medium",
                "severity": 6,
                "report_count": 1,
                "ai_summary": "Summary",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ]

        with patch("app.services.safety_service.supabase_service.rest_query") as mock_rq:
            async def fake_rest(table, method="GET", params=None, json_data=None):
                if table == "complaints":
                    assert params.get("citizen_id") == f"eq.{CITIZEN_1.id}"
                    assert params.get("safety_related") == "eq.true"
                    return mock_reports
                if table == "departments":
                    return [{"id": str(DEPT_PWD), "name": "Public Works Department"}]
                return []

            mock_rq.side_effect = fake_rest

            my_reports = await safety_service.get_my_safety_reports(CITIZEN_1)
            assert len(my_reports) == 1
            assert my_reports[0].citizen_id == CITIZEN_1.id
            assert my_reports[0].department_name == "Public Works Department"

        passed += 1
        print("PASS - Test 5: Citizen can retrieve their own reports")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 5: {e}")

    # -------------------------------------------------------------------------
    # Test 6: /mine and /my return equivalent authorized results
    # -------------------------------------------------------------------------
    try:
        sample_report_json = {
            "id": str(uuid4()),
            "citizen_id": str(CITIZEN_1.id),
            "title": "Route Equivalence Test",
            "description": "Pedestrian safety concern description",
            "latitude": 15.49,
            "longitude": 73.82,
            "category": "Unsafe public infrastructure",
            "issue_type": "Poor Lighting",
            "department_id": str(DEPT_PWD),
            "image_url": None,
            "safety_related": True,
            "safety_category": "Poor Lighting",
            "status": "Submitted",
            "priority": "Medium",
            "severity": 5,
            "report_count": 1,
            "ai_summary": "Summary",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Override dependency for citizen
        app.dependency_overrides[get_current_user] = lambda: CITIZEN_1
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            with patch("app.services.safety_service.supabase_service.rest_query") as mock_rq:
                async def fake_rest(table, method="GET", params=None, json_data=None):
                    if table == "complaints":
                        return [sample_report_json]
                    if table == "departments":
                        return [{"id": str(DEPT_PWD), "name": "Public Works Department"}]
                    return []

                mock_rq.side_effect = fake_rest

                resp_mine = await client.get("/api/v1/safety-reports/mine")
                resp_my = await client.get("/api/v1/safety-reports/my")

                assert resp_mine.status_code == 200, f"Expected 200 on /mine, got {resp_mine.status_code}"
                assert resp_my.status_code == 200, f"Expected 200 on /my, got {resp_my.status_code}"
                assert resp_mine.json() == resp_my.json(), "/mine and /my must return equivalent payloads"

        app.dependency_overrides.clear()
        passed += 1
        print("PASS - Test 6: /mine and /my return equivalent authorized results")
    except Exception as e:
        app.dependency_overrides.clear()
        failed += 1
        print(f"FAIL - Test 6: {e}")

    # -------------------------------------------------------------------------
    # Test 7: Citizen cannot access another citizen's report
    # -------------------------------------------------------------------------
    try:
        report_id = uuid4()
        other_report = {
            "id": str(report_id),
            "citizen_id": str(CITIZEN_1.id),  # Owned by Citizen 1
            "title": "Private Citizen 1 Report",
            "description": "Sensitive report text",
            "latitude": 15.49,
            "longitude": 73.82,
            "category": "Unsafe public infrastructure",
            "issue_type": "Poor Lighting",
            "department_id": str(DEPT_PWD),
            "image_url": None,
            "safety_related": True,
            "safety_category": "Poor Lighting",
            "status": "Submitted",
            "priority": "Medium",
            "severity": 5,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        with patch("app.services.safety_service.supabase_service.rest_query") as mock_rq:
            async def fake_rest(table, method="GET", params=None, json_data=None):
                if table == "complaints":
                    return [other_report]
                return []

            mock_rq.side_effect = fake_rest

            # Citizen 2 attempts to fetch Citizen 1's report
            try:
                await safety_service.get_safety_report_by_id(report_id, CITIZEN_2)
                assert False, "Should have raised HTTPException 403"
            except HTTPException as exc:
                assert exc.status_code == 403, f"Expected 403 Forbidden, got {exc.status_code}"
                assert "only view your own" in exc.detail.lower()

        passed += 1
        print("PASS - Test 7: Citizen cannot access another citizen's report (HTTP 403)")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 7: {e}")

    # -------------------------------------------------------------------------
    # Test 8: Ordinary officials cannot access the safety register
    # -------------------------------------------------------------------------
    try:
        # Check service level
        try:
            await safety_service.list_safety_reports_for_officer(ORDINARY_OFFICIAL)
            assert False, "Should have raised HTTPException 403"
        except HTTPException as exc:
            assert exc.status_code == 403
            assert "designated safety officers" in exc.detail.lower()

        # Check route level via AsyncClient with real dependency chain
        app.dependency_overrides[get_current_user] = lambda: ORDINARY_OFFICIAL
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/safety-reports")
            assert resp.status_code == 403
            assert "designated safety officials" in resp.json()["detail"].lower()

        app.dependency_overrides.clear()
        passed += 1
        print("PASS - Test 8: Ordinary officials cannot access the safety register (HTTP 403)")
    except Exception as e:
        app.dependency_overrides.clear()
        failed += 1
        print(f"FAIL - Test 8: {e}")

    # -------------------------------------------------------------------------
    # Test 9: Workers cannot access the safety register
    # -------------------------------------------------------------------------
    try:
        app.dependency_overrides[get_current_user] = lambda: WORKER_USER
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/safety-reports")
            assert resp.status_code == 403
            assert "required role" in resp.json()["detail"].lower()

        app.dependency_overrides.clear()
        passed += 1
        print("PASS - Test 9: Workers cannot access the safety register (HTTP 403)")
    except Exception as e:
        app.dependency_overrides.clear()
        failed += 1
        print(f"FAIL - Test 9: {e}")

    # -------------------------------------------------------------------------
    # Test 10: Designated safety officer can list reports
    # -------------------------------------------------------------------------
    try:
        sample_reports = [
            {
                "id": str(uuid4()),
                "citizen_id": str(CITIZEN_1.id),
                "title": "Safety Incident Alpha",
                "description": "Deserted path",
                "latitude": 15.49,
                "longitude": 73.82,
                "category": "Unsafe public infrastructure",
                "issue_type": "Deserted Bus Stop",
                "department_id": str(DEPT_PWD),
                "image_url": None,
                "safety_related": True,
                "safety_category": "Deserted Bus Stop",
                "status": "Submitted",
                "priority": "High",
                "severity": 8,
                "report_count": 1,
                "ai_summary": "Summary",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ]

        with patch("app.services.safety_service.supabase_service.rest_query") as mock_rq:
            async def fake_rest(table, method="GET", params=None, json_data=None):
                if table == "complaints":
                    assert params.get("safety_related") == "eq.true"
                    return sample_reports
                if table == "departments":
                    return [{"id": str(DEPT_PWD), "name": "Public Works Department"}]
                return []

            mock_rq.side_effect = fake_rest

            officer_reports = await safety_service.list_safety_reports_for_officer(SAFETY_OFFICER_CITYWIDE)
            assert len(officer_reports) == 1
            assert officer_reports[0].safety_category == "Deserted Bus Stop"

        passed += 1
        print("PASS - Test 10: Designated safety officer can list reports")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 10: {e}")

    # -------------------------------------------------------------------------
    # Test 11: Department-scoped safety officer cannot access another department's report
    # -------------------------------------------------------------------------
    try:
        # Officer Charlie is PWD. Tries to query Lighting department reports.
        try:
            await safety_service.list_safety_reports_for_officer(
                SAFETY_OFFICER_PWD,
                department_id=DEPT_LIGHTING,
            )
            assert False, "Should have raised HTTPException 403"
        except HTTPException as exc:
            assert exc.status_code == 403
            assert "another department" in exc.detail.lower()

        # Also test get_safety_report_by_id for report belonging to Lighting
        lighting_report = {
            "id": str(uuid4()),
            "citizen_id": str(CITIZEN_1.id),
            "title": "Lighting Dept Safety Report",
            "description": "Broken high-voltage lamp",
            "latitude": 15.49,
            "longitude": 73.82,
            "category": "Unsafe public infrastructure",
            "issue_type": "Lighting issue",
            "department_id": str(DEPT_LIGHTING),  # Different department!
            "image_url": None,
            "safety_related": True,
            "safety_category": "Lighting issue",
            "status": "Submitted",
            "priority": "High",
            "severity": 8,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        with patch("app.services.safety_service.supabase_service.rest_query", AsyncMock(return_value=[lighting_report])):
            try:
                await safety_service.get_safety_report_by_id(UUID(lighting_report["id"]), SAFETY_OFFICER_PWD)
                assert False, "Should have raised HTTPException 403"
            except HTTPException as exc:
                assert exc.status_code == 403
                assert "outside your department" in exc.detail.lower()

        passed += 1
        print("PASS - Test 11: Department-scoped safety officer cannot access another department's report (HTTP 403)")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 11: {e}")

    # -------------------------------------------------------------------------
    # Test 12: City-wide safety officer can access authorized municipal reports
    # -------------------------------------------------------------------------
    try:
        captured_params = {}
        with patch("app.services.safety_service.supabase_service.rest_query") as mock_rq:
            async def fake_rest(table, method="GET", params=None, json_data=None):
                nonlocal captured_params
                if table == "complaints":
                    captured_params = params
                    return sample_reports
                if table == "departments":
                    return [{"id": str(DEPT_PWD), "name": "Public Works Department"}]
                return []

            mock_rq.side_effect = fake_rest

            # City-wide officer can query any department or no department filter
            res_all = await safety_service.list_safety_reports_for_officer(SAFETY_OFFICER_CITYWIDE)
            assert "department_id" not in captured_params

            res_dept = await safety_service.list_safety_reports_for_officer(
                SAFETY_OFFICER_CITYWIDE, department_id=DEPT_LIGHTING
            )
            assert captured_params.get("department_id") == f"eq.{DEPT_LIGHTING}"

        passed += 1
        print("PASS - Test 12: City-wide safety officer can access authorized municipal reports across departments")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 12: {e}")

    # -------------------------------------------------------------------------
    # Test 13: Safety officer can retrieve individual report details
    # -------------------------------------------------------------------------
    try:
        rep_id = uuid4()
        pwd_report = {
            "id": str(rep_id),
            "citizen_id": str(CITIZEN_1.id),
            "title": "PWD Infrastructure Safety",
            "description": "Dangerous pothole at pedestrian crosswalk",
            "latitude": 15.49,
            "longitude": 73.82,
            "category": "Unsafe public infrastructure",
            "issue_type": "Unsafe Crossing",
            "department_id": str(DEPT_PWD),
            "image_url": None,
            "safety_related": True,
            "safety_category": "Unsafe Crossing",
            "status": "Submitted",
            "priority": "High",
            "severity": 8,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        mock_updates = [
            {
                "id": str(uuid4()),
                "complaint_id": str(rep_id),
                "actor_id": str(CITIZEN_1.id),
                "status": "Submitted",
                "remarks": "Safety report submitted: Unsafe Crossing",
                "created_at": "2026-11-14T01:00:00Z",
            }
        ]

        with patch("app.services.safety_service.supabase_service.rest_query") as mock_rq:
            async def fake_rest(table, method="GET", params=None, json_data=None):
                if table == "complaints":
                    return [pwd_report]
                if table == "complaint_updates":
                    return mock_updates
                if table == "profiles":
                    return [{"id": str(CITIZEN_1.id), "full_name": "Alice Citizen", "role": "citizen"}]
                if table == "departments":
                    return [{"id": str(DEPT_PWD), "name": "Public Works Department"}]
                return []

            mock_rq.side_effect = fake_rest

            detail = await safety_service.get_safety_report_by_id(rep_id, SAFETY_OFFICER_PWD)
            assert detail.id == rep_id
            assert len(detail.updates) == 1
            assert detail.updates[0].status == "Submitted"
            assert detail.updates[0].actor_name == "Alice Citizen"

        passed += 1
        print("PASS - Test 13: Safety officer can retrieve individual report details with timeline")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 13: {e}")

    # -------------------------------------------------------------------------
    # Test 14: Citizen cannot retrieve another report's details
    # -------------------------------------------------------------------------
    try:
        app.dependency_overrides[get_current_user] = lambda: CITIZEN_2
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            with patch("app.services.safety_service.supabase_service.rest_query") as mock_rq:
                async def fake_rest(table, method="GET", params=None, json_data=None):
                    if table == "complaints":
                        return [pwd_report]  # Owned by Citizen 1
                    return []

                mock_rq.side_effect = fake_rest

                resp = await client.get(f"/api/v1/safety-reports/{rep_id}")
                assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
                assert "only view your own" in resp.json()["detail"].lower()

        app.dependency_overrides.clear()
        passed += 1
        print("PASS - Test 14: Citizen cannot retrieve another report's details via API (HTTP 403)")
    except Exception as e:
        app.dependency_overrides.clear()
        failed += 1
        print(f"FAIL - Test 14: {e}")

    # -------------------------------------------------------------------------
    # Test 15: Safety officer can update investigation status
    # -------------------------------------------------------------------------
    try:
        update_data = SafetyInvestigationUpdate(
            status="Under Review",
            remarks="Investigating streetlight wiring on-site.",
        )

        updated_report_db = dict(pwd_report)
        updated_report_db["status"] = "Under Review"

        with patch("app.services.safety_service.supabase_service.rest_query") as mock_rq:
            async def fake_rest(table, method="GET", params=None, json_data=None):
                if table == "complaints" and method == "GET":
                    return [pwd_report]
                if table == "complaints" and method == "PATCH":
                    return [updated_report_db]
                if table == "complaint_updates" and method == "POST":
                    return [{"id": str(uuid4())}]
                if table == "departments":
                    return [{"id": str(DEPT_PWD), "name": "Public Works Department"}]
                return []

            mock_rq.side_effect = fake_rest

            result = await safety_service.update_safety_investigation_status(rep_id, SAFETY_OFFICER_PWD, update_data)
            assert result.status == "Under Review"

        passed += 1
        print("PASS - Test 15: Safety officer can update investigation status")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 15: {e}")

    # -------------------------------------------------------------------------
    # Test 16: Invalid status transitions are rejected
    # -------------------------------------------------------------------------
    try:
        # Invalid direct jump: Submitted -> Resolved
        invalid_update = SafetyInvestigationUpdate(
            status="Resolved",
            remarks="Premature resolution attempt without review.",
        )

        with patch("app.services.safety_service.supabase_service.rest_query", AsyncMock(return_value=[pwd_report])):
            try:
                await safety_service.update_safety_investigation_status(rep_id, SAFETY_OFFICER_PWD, invalid_update)
                assert False, "Should have rejected invalid status transition"
            except HTTPException as exc:
                assert exc.status_code == 400
                assert "invalid status transition" in exc.detail.lower()

        passed += 1
        print("PASS - Test 16: Invalid status transitions are rejected (HTTP 400)")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 16: {e}")

    # -------------------------------------------------------------------------
    # Test 17: History insertion failure triggers appropriate rollback
    # -------------------------------------------------------------------------
    try:
        valid_update = SafetyInvestigationUpdate(
            status="Under Review",
            remarks="Testing history rollback compensation.",
        )

        patch_calls = []

        with patch("app.services.safety_service.supabase_service.rest_query") as mock_rq:
            async def fake_rest(table, method="GET", params=None, json_data=None):
                if table == "complaints" and method == "GET":
                    return [pwd_report]
                if table == "complaints" and method == "PATCH":
                    patch_calls.append(json_data)
                    return [pwd_report]
                if table == "complaint_updates" and method == "POST":
                    # Simulate failure in history insert
                    return False
                return []

            mock_rq.side_effect = fake_rest

            try:
                await safety_service.update_safety_investigation_status(rep_id, SAFETY_OFFICER_PWD, valid_update)
                assert False, "Should have failed due to history insertion failure"
            except HTTPException as exc:
                assert exc.status_code == 500
                assert "rolled back" in exc.detail.lower()

            # Verify that compensating PATCH was executed to restore previous status
            assert len(patch_calls) >= 2, "Compensating rollback PATCH must be executed"
            rollback_call = patch_calls[-1]
            assert rollback_call.get("status") == pwd_report["status"], "Rolled back status must match original state"

        passed += 1
        print("PASS - Test 17: History insertion failure triggers appropriate compensating rollback")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 17: {e}")

    # -------------------------------------------------------------------------
    # Test 18: Image paths belonging to another user are rejected
    # -------------------------------------------------------------------------
    try:
        # Citizen 1 tries to attach Citizen 2's image
        other_user_image = f"complaints/{CITIZEN_2.id}/photo.jpg"
        stolen_img_report = SafetyReportCreate(
            description="Attempting to link another user's image to safety report.",
            latitude=15.49,
            longitude=73.82,
            safety_category="Poor Lighting",
            image_url=other_user_image,
        )

        try:
            await safety_service.create_safety_report(CITIZEN_1, stolen_img_report)
            assert False, "Should have raised HTTPException 403"
        except HTTPException as exc:
            assert exc.status_code == 403
            assert "uploaded by another user" in exc.detail.lower()

        passed += 1
        print("PASS - Test 18: Image paths belonging to another user are rejected (HTTP 403)")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 18: {e}")

    # -------------------------------------------------------------------------
    # Test 19: Unauthorized image access is rejected
    # -------------------------------------------------------------------------
    try:
        # Non-namespaced arbitrary path or directory traversal
        arbitrary_paths = [
            "arbitrary/path/exploit.jpg",
            "complaints/../admin/secrets.png",
            "/etc/passwd",
        ]
        rejected_paths = 0
        for p in arbitrary_paths:
            is_valid = storage_service.validate_image_ownership(p, str(CITIZEN_1.id))
            if not is_valid:
                rejected_paths += 1

        assert rejected_paths == len(arbitrary_paths)
        passed += 1
        print("PASS - Test 19: Unauthorized image storage paths are rejected")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 19: {e}")

    # -------------------------------------------------------------------------
    # Test 20: Signed URLs are generated only after authorization
    # -------------------------------------------------------------------------
    try:
        rep_with_img = dict(pwd_report)
        rep_with_img["image_url"] = f"complaints/{CITIZEN_1.id}/photo123.jpg"

        signed_url_generated = False

        async def fake_signed_url(path, expires_in=3600):
            nonlocal signed_url_generated
            signed_url_generated = True
            return f"https://supabase.co/storage/v1/object/sign/complaint-images/{path}?token=abc"

        with patch("app.services.safety_service.storage_service.create_signed_url", fake_signed_url), \
             patch("app.services.safety_service.supabase_service.rest_query") as mock_rq:

            async def fake_rest(table, method="GET", params=None, json_data=None):
                if table == "complaints":
                    return [rep_with_img]
                if table == "complaint_updates":
                    return []
                if table == "departments":
                    return [{"id": str(DEPT_PWD), "name": "Public Works Department"}]
                return []

            mock_rq.side_effect = fake_rest

            # Authorized retrieval by owner generates signed URL
            detail = await safety_service.get_safety_report_by_id(UUID(rep_with_img["id"]), CITIZEN_1)
            assert signed_url_generated is True
            assert detail.image_signed_url is not None

            # Reset flag
            signed_url_generated = False

            # Unauthorized retrieval by another user fails before signed URL creation
            try:
                await safety_service.get_safety_report_by_id(UUID(rep_with_img["id"]), CITIZEN_2)
            except HTTPException:
                pass
            assert signed_url_generated is False, "Signed URL must NOT be generated for unauthorized user"

        passed += 1
        print("PASS - Test 20: Signed URLs are generated only after authorization")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 20: {e}")

    # -------------------------------------------------------------------------
    # Test 21: Citizen cannot change priority or department through submission payload
    # -------------------------------------------------------------------------
    try:
        attempts_blocked = 0
        try:
            SafetyReportCreate(
                description="Test priority injection",
                latitude=15.4,
                longitude=73.8,
                safety_category="Poor Lighting",
                priority="Critical",
            )
        except ValidationError:
            attempts_blocked += 1

        try:
            SafetyReportCreate(
                description="Test department injection",
                latitude=15.4,
                longitude=73.8,
                safety_category="Poor Lighting",
                department_id=str(uuid4()),
            )
        except ValidationError:
            attempts_blocked += 1

        assert attempts_blocked == 2
        passed += 1
        print("PASS - Test 21: Citizen cannot change priority or department through submission payload")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 21: {e}")

    # -------------------------------------------------------------------------
    # Test 22: Query parameters cannot expand access
    # -------------------------------------------------------------------------
    try:
        # Officer Charlie (PWD) attempts to expand access to Lighting by query parameter
        try:
            await safety_service.list_safety_reports_for_officer(
                SAFETY_OFFICER_PWD,
                department_id=DEPT_LIGHTING,
            )
            assert False, "Should have rejected query parameter expansion with 403"
        except HTTPException as exc:
            assert exc.status_code == 403
            assert "not authorized" in exc.detail.lower()

        passed += 1
        print("PASS - Test 22: Query parameters cannot expand access (HTTP 403)")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 22: {e}")

    # -------------------------------------------------------------------------
    # Test 23: Complaint history is returned in correct order
    # -------------------------------------------------------------------------
    try:
        mock_timeline = [
            {
                "id": str(uuid4()),
                "complaint_id": str(rep_id),
                "actor_id": str(CITIZEN_1.id),
                "status": "Submitted",
                "remarks": "Initial safety submission",
                "created_at": "2026-11-14T01:00:00Z",
            },
            {
                "id": str(uuid4()),
                "complaint_id": str(rep_id),
                "actor_id": str(SAFETY_OFFICER_PWD.id),
                "status": "Under Review",
                "remarks": "Safety officer inspection begun",
                "created_at": "2026-11-14T02:00:00Z",
            },
            {
                "id": str(uuid4()),
                "complaint_id": str(rep_id),
                "actor_id": str(SAFETY_OFFICER_PWD.id),
                "status": "In Progress",
                "remarks": "Repair crew dispatched",
                "created_at": "2026-11-14T03:00:00Z",
            },
        ]

        with patch("app.services.safety_service.supabase_service.rest_query") as mock_rq:
            captured_order = None

            async def fake_rest(table, method="GET", params=None, json_data=None):
                nonlocal captured_order
                if table == "complaints":
                    return [pwd_report]
                if table == "complaint_updates":
                    captured_order = params.get("order")
                    return mock_timeline
                if table == "profiles":
                    return [
                        {"id": str(CITIZEN_1.id), "full_name": "Alice Citizen", "role": "citizen"},
                        {"id": str(SAFETY_OFFICER_PWD.id), "full_name": "Officer Charlie", "role": "official"},
                    ]
                if table == "departments":
                    return [{"id": str(DEPT_PWD), "name": "Public Works Department"}]
                return []

            mock_rq.side_effect = fake_rest

            detail = await safety_service.get_safety_report_by_id(rep_id, SAFETY_OFFICER_PWD)
            assert captured_order == "created_at.asc", "History updates must query with order=created_at.asc"
            assert len(detail.updates) == 3
            assert detail.updates[0].status == "Submitted"
            assert detail.updates[1].status == "Under Review"
            assert detail.updates[2].status == "In Progress"

        passed += 1
        print("PASS - Test 23: Complaint history is returned in correct chronological order")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 23: {e}")

    # -------------------------------------------------------------------------
    # Test 24: Existing M4-04 complaint lifecycle behavior remains intact
    # -------------------------------------------------------------------------
    try:
        from app.services.complaint_service import ALLOWED_TRANSITIONS, VALID_STATUSES

        assert "Submitted" in VALID_STATUSES
        assert "Under Review" in VALID_STATUSES
        assert "In Progress" in VALID_STATUSES
        assert "Resolved" in VALID_STATUSES
        assert "Rejected" in VALID_STATUSES
        assert "Under Review" in ALLOWED_TRANSITIONS["Submitted"]
        assert "Resolved" in ALLOWED_TRANSITIONS["In Progress"]
        assert "Resolved" not in ALLOWED_TRANSITIONS["Submitted"]  # direct skip illegal

        passed += 1
        print("PASS - Test 24: Existing M4-04 complaint lifecycle behavior remains intact")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 24: {e}")

    # -------------------------------------------------------------------------
    # Test 25: M4-06 safety-zone and map behavior remains intact
    # -------------------------------------------------------------------------
    try:
        # Generate 4 incidents clustered within 100 meters
        clustered_reports = [
            {
                "id": str(uuid4()),
                "latitude": 15.4980,
                "longitude": 73.8270,
                "safety_category": "Poor Lighting",
                "severity": 7,
                "status": "Submitted",
                "created_at": "2026-11-14T01:00:00Z",
            },
            {
                "id": str(uuid4()),
                "latitude": 15.4982,
                "longitude": 73.8271,
                "safety_category": "Poor Lighting",
                "severity": 8,
                "status": "Submitted",
                "created_at": "2026-11-14T01:30:00Z",
            },
            {
                "id": str(uuid4()),
                "latitude": 15.4981,
                "longitude": 73.8269,
                "safety_category": "Poor Lighting",
                "severity": 7,
                "status": "Submitted",
                "created_at": "2026-11-14T02:00:00Z",
            },
            {
                "id": str(uuid4()),
                "latitude": 15.4983,
                "longitude": 73.8272,
                "safety_category": "Poor Lighting",
                "severity": 6,
                "status": "Submitted",
                "created_at": "2026-11-14T02:30:00Z",
            },
        ]

        with patch("app.services.map_service.supabase_service.rest_query", AsyncMock(return_value=clustered_reports)):
            zones = await map_service.get_safety_zones(CITIZEN_1)
            assert len(zones) >= 1, "Cluster of 4 reports must produce at least 1 aggregated safety zone"
            assert zones[0].report_count >= 3, "Safety zone must have report_count >= 3"
            assert not hasattr(zones[0], "citizen_id"), "Aggregated safety zone must not expose citizen_id"

        passed += 1
        print("PASS - Test 25: M4-06 safety-zone and map privacy behavior remains intact")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 25: {e}")

    # -------------------------------------------------------------------------
    # Final Summary
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print(f"M4-07 Test Results: {passed}/{total} Passed, {failed} Failed")
    print("=" * 70)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
