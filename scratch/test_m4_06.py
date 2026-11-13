"""Comprehensive Test Suite for M4-06 Map and Traffic APIs.

Covers:
- Group 1: Map Complaints Authorization & PII Redaction (Tests 1–7)
- Group 2: Map Projects Visibility & Department Scoping (Tests 8–12)
- Group 3: Traffic Hotspot Listing, Creation & Validation (Tests 13–18)
- Group 4: Safety-Zone Privacy, k >= 3 Aggregation & Officer Granularity (Tests 19–26)
- Group 5: Route Registry & End-to-End FastAPI App Verification (Tests 27–30)
"""
import asyncio
import functools
import os
import sys

# Ensure all print statements flush immediately
print = functools.partial(print, flush=True)
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from fastapi import HTTPException
from pydantic import ValidationError

from app.api.deps import get_current_user, require_official
from app.main import app
from app.schemas.map import (
    AggregatedSafetyZoneResponse,
    MapComplaintMarker,
    MapProjectMarker,
    SafetyOfficerIncidentMarker,
    TrafficHotspotCreate,
    TrafficHotspotResponse,
)
from app.schemas.profile import ProfileResponse
from app.services.map_service import MapService, map_service

# Test IDs
DEPT_PWD = UUID("11111111-1111-1111-1111-111111111111")
DEPT_LIGHTING = UUID("44444444-4444-4444-4444-444444444444")
DEPT_OTHER = UUID("22222222-2222-2222-2222-222222222222")

CITIZEN_USER = ProfileResponse(
    id=uuid4(),
    full_name="Citizen Tester",
    role="citizen",
    department_id=None,
    is_safety_officer=False,
)

DEPT_OFFICIAL = ProfileResponse(
    id=uuid4(),
    full_name="PWD Official",
    role="official",
    department_id=DEPT_PWD,
    is_safety_officer=False,
)

GENERAL_OFFICIAL = ProfileResponse(
    id=uuid4(),
    full_name="City Administrator",
    role="official",
    department_id=None,
    is_safety_officer=False,
)

SAFETY_OFFICER = ProfileResponse(
    id=uuid4(),
    full_name="Designated Safety Officer",
    role="official",
    department_id=DEPT_LIGHTING,
    is_safety_officer=True,
)

WORKER_USER = ProfileResponse(
    id=uuid4(),
    full_name="Field Worker",
    role="worker",
    department_id=DEPT_PWD,
    is_safety_officer=False,
)

SAMPLE_DEPTS = [
    {"id": str(DEPT_PWD), "name": "Public Works Department"},
    {"id": str(DEPT_LIGHTING), "name": "Electricity & Lighting Department"},
    {"id": str(DEPT_OTHER), "name": "Solid Waste Management"},
]


async def run_all_tests():
    passed = 0
    failed = 0
    total = 30

    print("=" * 70)
    print("M4-06 Map & Traffic APIs Test Suite")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # Group 1: Map Complaints Authorization & PII Redaction (Tests 1–7)
    # -------------------------------------------------------------------------
    print("\n--- Group 1: Map Complaints Authorization & PII Redaction ---")

    # Test 1: Citizen receives non-safety complaints with zero PII
    try:
        service = MapService()
        mock_records = [
            {
                "id": str(uuid4()),
                "latitude": 15.401,
                "longitude": 73.815,
                "category": "Road Infrastructure",
                "status": "In Progress",
                "priority": "High",
                "department_id": str(DEPT_PWD),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "report_count": 2,
                "safety_related": False,
                "safety_category": None,
                "citizen_id": str(uuid4()),  # DB has it, service must exclude it
            }
        ]

        async def mock_rest_query(table, method="GET", params=None, json_data=None, use_service_role=True):
            if table == "departments":
                return SAMPLE_DEPTS
            if table == "complaints":
                # Ensure server enforced safety_related = eq.false
                assert params.get("safety_related") == "eq.false", f"Expected safety_related=eq.false, got {params}"
                return mock_records
            return []

        with patch("app.services.map_service.supabase_service.rest_query", side_effect=mock_rest_query):
            markers = await service.get_complaint_markers(current_user=CITIZEN_USER)
            assert len(markers) == 1
            marker = markers[0]
            assert isinstance(marker, MapComplaintMarker)
            assert marker.department_name == "Public Works Department"
            assert marker.safety_related is None  # Redacted
            assert marker.safety_category is None  # Redacted
            assert not hasattr(marker, "citizen_id")  # Not in schema
            passed += 1
            print("PASS - Test 1: Citizen receives non-safety complaints with PII excluded and safety fields redacted")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 1: {e}")

    # Test 2: Citizen requesting safety_related=true is rejected with HTTP 403
    try:
        service = MapService()
        try:
            await service.get_complaint_markers(current_user=CITIZEN_USER, safety_related=True)
            failed += 1
            print("FAIL - Test 2: Expected HTTP 403 for citizen querying safety_related=True")
        except HTTPException as he:
            assert he.status_code == 403
            assert "safety officer authorization" in he.detail.lower()
            passed += 1
            print("PASS - Test 2: Citizen requesting safety_related=true rejected with HTTP 403")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 2: {e}")

    # Test 3: Ordinary official requesting safety_related=true is rejected with HTTP 403
    try:
        service = MapService()
        try:
            await service.get_complaint_markers(current_user=DEPT_OFFICIAL, safety_related=True)
            failed += 1
            print("FAIL - Test 3: Expected HTTP 403 for ordinary official querying safety_related=True")
        except HTTPException as he:
            assert he.status_code == 403
            assert "safety officer authorization" in he.detail.lower()
            passed += 1
            print("PASS - Test 3: Ordinary official requesting safety_related=true rejected with HTTP 403")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 3: {e}")

    # Test 4: Department official complaint scoping (scoped to own department, cannot query other dept)
    try:
        service = MapService()
        # Querying other department should fail with 403
        try:
            await service.get_complaint_markers(current_user=DEPT_OFFICIAL, department_id=DEPT_OTHER)
            failed += 1
            print("FAIL - Test 4: Expected HTTP 403 when department official queries other department")
        except HTTPException as he:
            assert he.status_code == 403
            assert "not authorized to view complaints for other departments" in he.detail.lower()

        # Querying without param should enforce own department
        async def mock_dept_query(table, method="GET", params=None, json_data=None, use_service_role=True):
            if table == "departments":
                return SAMPLE_DEPTS
            if table == "complaints":
                assert params.get("department_id") == f"eq.{DEPT_PWD}"
                assert params.get("safety_related") == "eq.false"
                return []
            return []

        with patch("app.services.map_service.supabase_service.rest_query", side_effect=mock_dept_query):
            await service.get_complaint_markers(current_user=DEPT_OFFICIAL)

        passed += 1
        print("PASS - Test 4: Department official complaint scoping strictly enforced")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 4: {e}")

    # Test 5: General official can view complaints across departments
    try:
        service = MapService()

        async def mock_gen_query(table, method="GET", params=None, json_data=None, use_service_role=True):
            if table == "departments":
                return SAMPLE_DEPTS
            if table == "complaints":
                assert "department_id" not in params  # No department constraint added by default
                assert params.get("safety_related") == "eq.false"
                return []
            return []

        with patch("app.services.map_service.supabase_service.rest_query", side_effect=mock_gen_query):
            await service.get_complaint_markers(current_user=GENERAL_OFFICIAL)

        passed += 1
        print("PASS - Test 5: General official can view complaints across all departments")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 5: {e}")

    # Test 6: Safety officer can access safety complaints with safety category
    try:
        service = MapService()
        safety_rec = {
            "id": str(uuid4()),
            "latitude": 15.405,
            "longitude": 73.818,
            "category": "Street Lighting",
            "status": "Submitted",
            "priority": "Critical",
            "department_id": str(DEPT_LIGHTING),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "report_count": 1,
            "safety_related": True,
            "safety_category": "Lighting",
        }

        async def mock_safety_query(table, method="GET", params=None, json_data=None, use_service_role=True):
            if table == "departments":
                return SAMPLE_DEPTS
            if table == "complaints":
                return [safety_rec]
            return []

        with patch("app.services.map_service.supabase_service.rest_query", side_effect=mock_safety_query):
            markers = await service.get_complaint_markers(current_user=SAFETY_OFFICER, safety_related=True)
            assert len(markers) == 1
            assert markers[0].safety_related is True
            assert markers[0].safety_category == "Lighting"
            assert markers[0].department_name == "Electricity & Lighting Department"
        passed += 1
        print("PASS - Test 6: Safety officer retrieves authorized safety complaint markers with safety_category")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 6: {e}")

    # Test 7: Worker is rejected from complaints endpoint with HTTP 403
    try:
        service = MapService()
        try:
            await service.get_complaint_markers(current_user=WORKER_USER)
            failed += 1
            print("FAIL - Test 7: Expected HTTP 403 for worker accessing complaint markers")
        except HTTPException as he:
            assert he.status_code == 403
            assert "workers do not have access" in he.detail.lower()
            passed += 1
            print("PASS - Test 7: Worker rejected from complaint map endpoint with HTTP 403")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 7: {e}")

    # -------------------------------------------------------------------------
    # Group 2: Map Projects Visibility & Department Scoping (Tests 8–12)
    # -------------------------------------------------------------------------
    print("\n--- Group 2: Map Projects Visibility & Department Scoping ---")

    sample_project = {
        "id": str(uuid4()),
        "title": "MG Road Drainage",
        "description": "Drainage repair project",
        "department_id": str(DEPT_PWD),
        "latitude": 15.402,
        "longitude": 73.816,
        "status": "Ongoing",
        "start_date": "2026-10-01",
        "expected_end_date": "2026-12-31",
        "is_published": True,
    }

    # Test 8: Citizen sees only published projects
    try:
        service = MapService()

        async def mock_proj_citizen(table, method="GET", params=None, json_data=None, use_service_role=True):
            if table == "departments":
                return SAMPLE_DEPTS
            if table == "projects":
                assert params.get("is_published") == "eq.true"
                return [sample_project]
            return []

        with patch("app.services.map_service.supabase_service.rest_query", side_effect=mock_proj_citizen):
            markers = await service.get_project_markers(current_user=CITIZEN_USER)
            assert len(markers) == 1
            assert markers[0].is_published is True
            assert markers[0].department_name == "Public Works Department"
        passed += 1
        print("PASS - Test 8: Citizen sees only published projects")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 8: {e}")

    # Test 9: Worker sees only published projects
    try:
        service = MapService()

        async def mock_proj_worker(table, method="GET", params=None, json_data=None, use_service_role=True):
            if table == "departments":
                return SAMPLE_DEPTS
            if table == "projects":
                assert params.get("is_published") == "eq.true"
                return [sample_project]
            return []

        with patch("app.services.map_service.supabase_service.rest_query", side_effect=mock_proj_worker):
            markers = await service.get_project_markers(current_user=WORKER_USER)
            assert len(markers) == 1
        passed += 1
        print("PASS - Test 9: Worker sees only published projects")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 9: {e}")

    # Test 10: Department official sees published projects OR own department projects
    try:
        service = MapService()

        async def mock_proj_official(table, method="GET", params=None, json_data=None, use_service_role=True):
            if table == "departments":
                return SAMPLE_DEPTS
            if table == "projects":
                assert params.get("or") == f"(is_published.eq.true,department_id.eq.{DEPT_PWD})"
                return [sample_project]
            return []

        with patch("app.services.map_service.supabase_service.rest_query", side_effect=mock_proj_official):
            markers = await service.get_project_markers(current_user=DEPT_OFFICIAL)
            assert len(markers) == 1
        passed += 1
        print("PASS - Test 10: Department official can view published and own department unpublished projects")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 10: {e}")

    # Test 11: General official sees all projects without restriction
    try:
        service = MapService()

        async def mock_proj_gen(table, method="GET", params=None, json_data=None, use_service_role=True):
            if table == "departments":
                return SAMPLE_DEPTS
            if table == "projects":
                assert "is_published" not in params
                assert "or" not in params
                return [sample_project]
            return []

        with patch("app.services.map_service.supabase_service.rest_query", side_effect=mock_proj_gen):
            markers = await service.get_project_markers(current_user=GENERAL_OFFICIAL)
            assert len(markers) == 1
        passed += 1
        print("PASS - Test 11: General official sees all projects")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 11: {e}")

    # Test 12: Project filters (status and department) narrow results
    try:
        service = MapService()

        async def mock_proj_filter(table, method="GET", params=None, json_data=None, use_service_role=True):
            if table == "departments":
                return SAMPLE_DEPTS
            if table == "projects":
                assert params.get("department_id") == f"eq.{DEPT_PWD}"
                assert params.get("status") == "eq.Ongoing"
                return [sample_project]
            return []

        with patch("app.services.map_service.supabase_service.rest_query", side_effect=mock_proj_filter):
            markers = await service.get_project_markers(
                current_user=GENERAL_OFFICIAL, department_id=DEPT_PWD, status_filter="Ongoing"
            )
            assert len(markers) == 1
        passed += 1
        print("PASS - Test 12: Project filters (status and department) narrow queries correctly")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 12: {e}")

    # -------------------------------------------------------------------------
    # Group 3: Traffic Hotspot Listing, Creation & Validation (Tests 13–18)
    # -------------------------------------------------------------------------
    print("\n--- Group 3: Traffic Hotspot Listing, Creation & Validation ---")

    sample_hotspot = {
        "id": str(uuid4()),
        "latitude": 15.401,
        "longitude": 73.815,
        "congestion_level": "High",
        "source": "demo",
        "description": "Market Cross Junction bottleneck",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Test 13: Traffic hotspot listing returns demo source explicitly
    try:
        service = MapService()

        async def mock_hotspot_get(table, method="GET", params=None, json_data=None, use_service_role=True):
            if table == "traffic_hotspots":
                return [sample_hotspot]
            return []

        with patch("app.services.map_service.supabase_service.rest_query", side_effect=mock_hotspot_get):
            hotspots = await service.get_traffic_hotspots()
            assert len(hotspots) == 1
            assert hotspots[0].source == "demo"
            assert hotspots[0].congestion_level == "High"
        passed += 1
        print("PASS - Test 13: Traffic hotspots retrieved with demo source explicitly preserved")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 13: {e}")

    # Test 14: Traffic hotspot query filtering by congestion_level and source
    try:
        service = MapService()

        async def mock_hotspot_filter(table, method="GET", params=None, json_data=None, use_service_role=True):
            if table == "traffic_hotspots":
                assert params.get("congestion_level") == "eq.High"
                assert params.get("source") == "eq.demo"
                return [sample_hotspot]
            return []

        with patch("app.services.map_service.supabase_service.rest_query", side_effect=mock_hotspot_filter):
            hotspots = await service.get_traffic_hotspots(congestion_level="High", source="demo")
            assert len(hotspots) == 1
        passed += 1
        print("PASS - Test 14: Traffic hotspot query filters applied accurately")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 14: {e}")

    # Test 15: Official creates demo traffic hotspot successfully
    try:
        service = MapService()
        create_payload = TrafficHotspotCreate(
            latitude=15.405,
            longitude=73.82,
            congestion_level="Medium",
            description="Patto Plaza bridge entry backup",
            source="demo",
        )

        async def mock_hotspot_post(table, method="GET", params=None, json_data=None, use_service_role=True):
            if table == "traffic_hotspots" and method == "POST":
                assert json_data["source"] == "demo"
                assert json_data["congestion_level"] == "Medium"
                created_record = {
                    "id": str(uuid4()),
                    **json_data,
                    "observed_at": datetime.now(timezone.utc).isoformat(),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                return [created_record]
            return []

        with patch("app.services.map_service.supabase_service.rest_query", side_effect=mock_hotspot_post):
            res = await service.create_traffic_hotspot(data=create_payload, official=DEPT_OFFICIAL)
            assert res.congestion_level == "Medium"
            assert res.source == "demo"
        passed += 1
        print("PASS - Test 15: Official can create demo traffic hotspot")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 15: {e}")

    # Test 16: Non-official cannot create traffic hotspot (HTTP 403)
    try:
        service = MapService()
        create_payload = TrafficHotspotCreate(
            latitude=15.405,
            longitude=73.82,
            congestion_level="Medium",
            description="Patto Plaza bridge entry backup",
        )
        try:
            await service.create_traffic_hotspot(data=create_payload, official=CITIZEN_USER)
            failed += 1
            print("FAIL - Test 16: Expected HTTP 403 for citizen creating traffic hotspot")
        except HTTPException as he:
            assert he.status_code == 403
            assert "only municipal officials" in he.detail.lower()
            passed += 1
            print("PASS - Test 16: Citizen rejected from creating traffic hotspot with HTTP 403")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 16: {e}")

    # Test 17: Pydantic coordinate and congestion level validation
    try:
        # Invalid latitude (> 90)
        try:
            TrafficHotspotCreate(
                latitude=95.0,
                longitude=73.8,
                congestion_level="High",
                description="Invalid latitude coordinate test",
            )
            failed += 1
            print("FAIL - Test 17a: Expected ValidationError for lat > 90")
        except ValidationError:
            pass

        # Invalid congestion level
        try:
            TrafficHotspotCreate(
                latitude=15.4,
                longitude=73.8,
                congestion_level="Extreme",
                description="Invalid congestion level test",
            )
            failed += 1
            print("FAIL - Test 17b: Expected ValidationError for congestion_level='Extreme'")
        except ValidationError:
            pass

        # Short description (< 5 chars)
        try:
            TrafficHotspotCreate(
                latitude=15.4,
                longitude=73.8,
                congestion_level="High",
                description="Bad",
            )
            failed += 1
            print("FAIL - Test 17c: Expected ValidationError for description < 5 chars")
        except ValidationError:
            pass

        passed += 1
        print("PASS - Test 17: Pydantic coordinates, congestion level, and description length validated")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 17: {e}")

    # Test 18: Source must be strictly 'demo' for MVP
    try:
        try:
            TrafficHotspotCreate(
                latitude=15.4,
                longitude=73.8,
                congestion_level="High",
                description="Attempting to claim live sensor source",
                source="live_sensor",
            )
            failed += 1
            print("FAIL - Test 18: Expected ValidationError for source != 'demo'")
        except ValidationError as ve:
            assert "source must be 'demo' for this mvp" in str(ve).lower()
            passed += 1
            print("PASS - Test 18: Source strictly restricted to 'demo' for MVP")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 18: {e}")

    # -------------------------------------------------------------------------
    # Group 4: Safety-Zone Privacy, k >= 3 Aggregation & Officer Granularity (Tests 19–26)
    # -------------------------------------------------------------------------
    print("\n--- Group 4: Safety-Zone Privacy, k >= 3 Aggregation & Officer Granularity ---")

    # Test 19: Safety clusters with 1 report are completely suppressed
    try:
        service = MapService()
        # Single safety report in cell (15.40, 73.81)
        mock_isolated_report = [
            {
                "latitude": 15.401,
                "longitude": 73.814,
                "category": "Street Lighting",
                "safety_category": "Lighting",
                "status": "Submitted",
                "report_count": 1,
            }
        ]

        async def mock_single_safety(table, method="GET", params=None, json_data=None, use_service_role=True):
            if table == "complaints":
                assert params.get("status") == "neq.Rejected"
                return mock_isolated_report
            return []

        with patch("app.services.map_service.supabase_service.rest_query", side_effect=mock_single_safety):
            clusters = await service.get_safety_zones(current_user=CITIZEN_USER)
            assert len(clusters) == 0, f"Expected 0 clusters (k=1 suppressed), got {len(clusters)}"
        passed += 1
        print("PASS - Test 19: Safety cluster with 1 report is completely suppressed")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 19: {e}")

    # Test 20: Safety clusters with 2 reports are completely suppressed
    try:
        service = MapService()
        # Two safety reports in cell (15.40, 73.81)
        mock_two_reports = [
            {
                "latitude": 15.401,
                "longitude": 73.814,
                "category": "Street Lighting",
                "safety_category": "Lighting",
                "status": "Submitted",
                "report_count": 1,
            },
            {
                "latitude": 15.404,
                "longitude": 73.811,
                "category": "Street Lighting",
                "safety_category": "Lighting",
                "status": "Under Review",
                "report_count": 1,
            },
        ]

        async def mock_two_safety(table, method="GET", params=None, json_data=None, use_service_role=True):
            if table == "complaints":
                return mock_two_reports
            return []

        with patch("app.services.map_service.supabase_service.rest_query", side_effect=mock_two_safety):
            clusters = await service.get_safety_zones(current_user=CITIZEN_USER)
            assert len(clusters) == 0, f"Expected 0 clusters (k=2 suppressed), got {len(clusters)}"
        passed += 1
        print("PASS - Test 20: Safety cluster with 2 reports is completely suppressed")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 20: {e}")

    # Test 21: Safety clusters with 3 reports are returned with rounded coordinates
    try:
        service = MapService()
        mock_three_reports = [
            {
                "latitude": 15.40123,
                "longitude": 73.81456,
                "category": "Street Lighting",
                "safety_category": "Lighting",
                "status": "Submitted",
                "report_count": 1,
            },
            {
                "latitude": 15.40456,
                "longitude": 73.81123,
                "category": "Street Lighting",
                "safety_category": "Lighting",
                "status": "Under Review",
                "report_count": 1,
            },
            {
                "latitude": 15.40234,
                "longitude": 73.81345,
                "category": "Street Lighting",
                "safety_category": "Lighting",
                "status": "Assigned",
                "report_count": 1,
            },
        ]

        async def mock_three_safety(table, method="GET", params=None, json_data=None, use_service_role=True):
            if table == "complaints":
                return mock_three_reports
            return []

        with patch("app.services.map_service.supabase_service.rest_query", side_effect=mock_three_safety):
            clusters = await service.get_safety_zones(current_user=CITIZEN_USER)
            assert len(clusters) == 1
            cluster = clusters[0]
            assert isinstance(cluster, AggregatedSafetyZoneResponse)
            assert cluster.report_count == 3
            assert cluster.category == "Lighting Issue"
            # Coordinates MUST be rounded to exactly 2 decimal places
            assert cluster.latitude == 15.40
            assert cluster.longitude == 73.81
            assert "lighting inspection" in cluster.suggested_action.lower()
        passed += 1
        print("PASS - Test 21: Safety cluster with 3 reports returned with coordinates rounded to 2 decimal places")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 21: {e}")

    # Test 22: Public aggregate response contains no individual identifiers or raw descriptions
    try:
        # Inspect AggregatedSafetyZoneResponse schema fields
        fields = AggregatedSafetyZoneResponse.model_fields.keys()
        forbidden_fields = {"id", "citizen_id", "complaint_id", "description", "created_at", "user_id"}
        leaked = forbidden_fields.intersection(fields)
        assert len(leaked) == 0, f"Leaked forbidden fields in aggregate response: {leaked}"
        passed += 1
        print("PASS - Test 22: Public aggregate response strictly omits complaint IDs, citizen IDs, and raw text")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 22: {e}")

    # Test 23: Rejected safety complaints are excluded from safety-zone aggregation
    try:
        service = MapService()

        async def mock_rejected_filter(table, method="GET", params=None, json_data=None, use_service_role=True):
            if table == "complaints":
                # Verify that status.neq.Rejected is requested
                assert params.get("status") == "neq.Rejected"
                return []
            return []

        with patch("app.services.map_service.supabase_service.rest_query", side_effect=mock_rejected_filter):
            await service.get_safety_zones(current_user=CITIZEN_USER)
        passed += 1
        print("PASS - Test 23: Rejected complaints excluded from safety-zone aggregation")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 23: {e}")

    # Test 24: Designated safety officer receives authorized granular safety incident markers
    try:
        service = MapService()
        granular_report = {
            "id": str(uuid4()),
            "latitude": 15.401234,
            "longitude": 73.815678,
            "category": "Street Lighting",
            "safety_category": "Lighting",
            "status": "Submitted",
            "priority": "Critical",
            "severity": 9,
            "report_count": 1,
            "department_id": str(DEPT_LIGHTING),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        async def mock_officer_safety(table, method="GET", params=None, json_data=None, use_service_role=True):
            if table == "departments":
                return SAMPLE_DEPTS
            if table == "complaints":
                assert params.get("safety_related") == "eq.true"
                assert params.get("status") == "neq.Rejected"
                assert params.get("department_id") == f"eq.{DEPT_LIGHTING}"
                return [granular_report]
            return []

        with patch("app.services.map_service.supabase_service.rest_query", side_effect=mock_officer_safety):
            markers = await service.get_safety_zones(current_user=SAFETY_OFFICER)
            assert len(markers) == 1
            marker = markers[0]
            assert isinstance(marker, SafetyOfficerIncidentMarker)
            assert marker.latitude == 15.401234  # Exact coordinate
            assert marker.longitude == 73.815678  # Exact coordinate
            assert marker.safety_category == "Lighting"
            assert marker.severity == 9
            assert marker.department_name == "Electricity & Lighting Department"
        passed += 1
        print("PASS - Test 24: Safety officer receives granular authorized safety incident markers")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 24: {e}")

    # Test 25: Worker is rejected from safety-zones endpoint with HTTP 403
    try:
        service = MapService()
        try:
            await service.get_safety_zones(current_user=WORKER_USER)
            failed += 1
            print("FAIL - Test 25: Expected HTTP 403 for worker accessing safety zones")
        except HTTPException as he:
            assert he.status_code == 403
            assert "workers do not have access" in he.detail.lower()
            passed += 1
            print("PASS - Test 25: Worker rejected from safety zones with HTTP 403")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 25: {e}")

    # Test 26: Ordinary official receives aggregated clusters, not individual incident records
    try:
        service = MapService()
        mock_three_reports = [
            {
                "latitude": 15.401,
                "longitude": 73.814,
                "category": "Street Lighting",
                "safety_category": "Lighting",
                "status": "Submitted",
                "report_count": 1,
            },
            {
                "latitude": 15.402,
                "longitude": 73.812,
                "category": "Street Lighting",
                "safety_category": "Lighting",
                "status": "Under Review",
                "report_count": 1,
            },
            {
                "latitude": 15.403,
                "longitude": 73.813,
                "category": "Street Lighting",
                "safety_category": "Lighting",
                "status": "Assigned",
                "report_count": 1,
            },
        ]

        async def mock_ord_safety(table, method="GET", params=None, json_data=None, use_service_role=True):
            if table == "complaints":
                return mock_three_reports
            return []

        with patch("app.services.map_service.supabase_service.rest_query", side_effect=mock_ord_safety):
            clusters = await service.get_safety_zones(current_user=DEPT_OFFICIAL)
            assert len(clusters) == 1
            assert isinstance(clusters[0], AggregatedSafetyZoneResponse)
            assert not isinstance(clusters[0], SafetyOfficerIncidentMarker)
        passed += 1
        print("PASS - Test 26: Ordinary official receives aggregated cluster response without granular incident records")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 26: {e}")

    # -------------------------------------------------------------------------
    # Group 5: Route Registry & End-to-End FastAPI App Verification (Tests 27–30)
    # -------------------------------------------------------------------------
    print("\n--- Group 5: Route Registry & End-to-End FastAPI App Verification ---")

    # Test 27: Verify all 5 routes are properly registered in FastAPI app
    try:
        openapi_paths = app.openapi()["paths"]
        expected_routes = [
            "/api/v1/map/complaints",
            "/api/v1/map/projects",
            "/api/v1/map/hotspots",
            "/api/v1/map/safety-zones",
        ]
        for er in expected_routes:
            assert er in openapi_paths, f"Missing route {er} in FastAPI routes: {list(openapi_paths.keys())}"
        passed += 1
        print("PASS - Test 27: All 5 map routes registered under /api/v1/map prefix")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 27: {e}")

    # Test 28: End-to-end GET /api/v1/map/hotspots via dependency override
    try:
        import httpx

        app.dependency_overrides[get_current_user] = lambda: CITIZEN_USER
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            with patch("app.services.map_service.supabase_service.rest_query", return_value=[sample_hotspot]):
                resp = await client.get("/api/v1/map/hotspots")
                assert resp.status_code == 200
                data = resp.json()
                assert len(data) == 1
                assert data[0]["source"] == "demo"
        app.dependency_overrides.clear()
        passed += 1
        print("PASS - Test 28: End-to-end GET /api/v1/map/hotspots returns 200 with demo data")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 28: {e}")

    # Test 29: End-to-end POST /api/v1/map/hotspots official creation via AsyncClient
    try:
        import httpx

        app.dependency_overrides[require_official] = lambda: DEPT_OFFICIAL
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created_hotspot_record = {
                "id": str(uuid4()),
                "latitude": 15.41,
                "longitude": 73.82,
                "congestion_level": "High",
                "source": "demo",
                "description": "Panaji Bus Stand intersection evening rush",
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            with patch("app.services.map_service.supabase_service.rest_query", return_value=[created_hotspot_record]):
                resp = await client.post(
                    "/api/v1/map/hotspots",
                    json={
                        "latitude": 15.41,
                        "longitude": 73.82,
                        "congestion_level": "High",
                        "description": "Panaji Bus Stand intersection evening rush",
                        "source": "demo",
                    },
                )
                assert resp.status_code == 201
                data = resp.json()
                assert data["congestion_level"] == "High"
                assert data["source"] == "demo"
        app.dependency_overrides.clear()
        passed += 1
        print("PASS - Test 29: End-to-end POST /api/v1/map/hotspots creates demo record and returns 201")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 29: {e}")

    # Test 30: End-to-end worker rejected from /api/v1/map/complaints with HTTP 403 via AsyncClient
    try:
        import httpx

        app.dependency_overrides[get_current_user] = lambda: WORKER_USER
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/map/complaints")
            assert resp.status_code == 403
            assert "workers do not have access" in resp.json()["detail"].lower()
        app.dependency_overrides.clear()
        passed += 1
        print("PASS - Test 30: End-to-end worker rejected from /api/v1/map/complaints with HTTP 403")
    except Exception as e:
        failed += 1
        print(f"FAIL - Test 30: {e}")

    # -------------------------------------------------------------------------
    # Final Summary
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print(f"M4-06 Test Results: {passed}/{total} Passed, {failed} Failed")
    print("=" * 70)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
