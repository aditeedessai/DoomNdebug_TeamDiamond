"""Comprehensive Test Suite for M4-04 AI, Priority, and Duplicate Integration.

Tests cover:
Group 1: AI-Assisted Complaint Creation (Tests 1–10)
Group 2: Priority Calculation (Tests 11–13)
Group 3: Advisory Duplicate Detection (Tests 14–18)
Group 4: Official Duplicate Linking (Tests 19–25)
Group 5: Hardened Rollback, Candidate Keys & Concurrency Protection (Tests 26–38)
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

# Windows event loop configuration for socket compatibility
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from fastapi import HTTPException
from app.schemas.ai import AIAnalysisRequest, AIAnalysisResponse
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintDetailResponse,
    ComplaintResponse,
    ComplaintUpdateItem,
    DuplicateLinkRequest,
    OfficialStatusUpdate,
)
from app.schemas.profile import ProfileResponse
from app.services.complaint_service import ComplaintService, complaint_service
from app.services.priority_service import priority_service

# Fixed UUIDs for test reproducibility
CITIZEN_ID = uuid4()
OTHER_CITIZEN_ID = uuid4()
PWD_DEPT_ID = uuid4()
SANITATION_DEPT_ID = uuid4()
PWD_OFFICIAL_ID = uuid4()
SANITATION_OFFICIAL_ID = uuid4()
GENERAL_OFFICIAL_ID = uuid4()
SAFETY_OFFICER_ID = uuid4()
WORKER_ID = uuid4()

citizen_user = ProfileResponse(
    id=CITIZEN_ID,
    full_name="Alice Citizen",
    role="citizen",
    department_id=None,
    is_safety_officer=False,
)

pwd_official = ProfileResponse(
    id=PWD_OFFICIAL_ID,
    full_name="Dave PWD Official",
    role="official",
    department_id=PWD_DEPT_ID,
    is_safety_officer=False,
)

sanitation_official = ProfileResponse(
    id=SANITATION_OFFICIAL_ID,
    full_name="Sam Sanitation Official",
    role="official",
    department_id=SANITATION_DEPT_ID,
    is_safety_officer=False,
)

safety_officer = ProfileResponse(
    id=SAFETY_OFFICER_ID,
    full_name="Sarah Safety Officer",
    role="official",
    department_id=PWD_DEPT_ID,
    is_safety_officer=True,
)

worker_user = ProfileResponse(
    id=WORKER_ID,
    full_name="Mike Field Worker",
    role="worker",
    department_id=PWD_DEPT_ID,
    is_safety_officer=False,
)


def make_mock_complaint(
    complaint_id: UUID,
    citizen_id: UUID = CITIZEN_ID,
    department_id: UUID = PWD_DEPT_ID,
    status: str = "Submitted",
    severity: int = 5,
    report_count: int = 1,
    priority: str = "Medium",
    safety_related: bool = False,
    master_incident_id: UUID = None,
    ai_summary: str = None,
):
    now_str = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(complaint_id),
        "citizen_id": str(citizen_id),
        "title": "Large pothole on 4th Main",
        "description": "Hazardous road crater causing traffic disruption",
        "latitude": 15.498,
        "longitude": 73.827,
        "category": "Potholes, damaged roads, footpaths",
        "issue_type": "Pothole",
        "department_id": str(department_id) if department_id else None,
        "severity": severity,
        "priority": priority,
        "status": status,
        "master_incident_id": str(master_incident_id) if master_incident_id else None,
        "report_count": report_count,
        "safety_related": safety_related,
        "safety_category": "Pedestrian accessibility issue" if safety_related else None,
        "ai_summary": ai_summary,
        "image_url": None,
        "created_at": now_str,
        "updated_at": now_str,
    }


# ==============================================================================
# GROUP 1: AI-ASSISTED COMPLAINT CREATION (TESTS 1–10)
# ==============================================================================

def test_1_successful_ai_creation():
    """Test 1: Successful complaint creation with valid AI analysis output."""
    print("\n--- Test 1: Successful Complaint Creation with Valid AI Analysis ---")
    service = ComplaintService()
    cid = uuid4()

    mock_ai = AIAnalysisResponse(
        suggested_title="Damaged Road Surface",
        category="Potholes, damaged roads, footpaths",
        issue_type="Pothole",
        department="Public Works Department",
        severity=7,
        is_safety_related=False,
        safety_category=None,
        summary="AI detected deep road surface pothole requiring asphalt restoration.",
        recommended_action="Dispatch asphalt patch team to repair road crater.",
        language="English",
    )

    created_record = make_mock_complaint(
        complaint_id=cid,
        department_id=PWD_DEPT_ID,
        severity=7,
        priority="High",
        ai_summary=mock_ai.summary,
    )

    with patch("app.services.complaint_service.ai_service.analyze_complaint", new_callable=AsyncMock) as mock_analyze, \
         patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:

        mock_analyze.return_value = mock_ai
        mock_query.side_effect = [
            [{"id": str(PWD_DEPT_ID)}],       # 1. Dept lookup by name
            [created_record],                  # 2. Insert complaint
            [{"id": str(uuid4())}],           # 3. Insert complaint_updates initial history
        ]

        req = ComplaintCreate(
            title="Road damage",
            description="Big crater on main road",
            latitude=15.498,
            longitude=73.827,
            category="Other",
            issue_type="General Civic Concern",
        )

        res = asyncio.run(service.create_complaint(citizen_user, req))

        assert res.id == cid
        assert res.department_id == PWD_DEPT_ID
        assert res.severity == 7
        assert res.priority == "High"
        assert res.ai_summary == mock_ai.summary
        print("[PASS] Test 1: Complaint successfully created with AI integration")


def test_2_ai_summary_mapping():
    """Test 2: Correct mapping of AI summary to ai_summary column in DB payload."""
    print("\n--- Test 2: AI Summary Mapping to DB Column ---")
    service = ComplaintService()
    cid = uuid4()

    mock_ai = AIAnalysisResponse(
        suggested_title="Pothole Report",
        category="Potholes, damaged roads, footpaths",
        issue_type="Pothole",
        department="Public Works Department",
        severity=6,
        is_safety_related=False,
        safety_category=None,
        summary="Accurate structural damage summary generated by AI pipeline.",
        recommended_action="Inspect road structure and patch depression.",
        language="English",
    )

    created_record = make_mock_complaint(complaint_id=cid, ai_summary=mock_ai.summary)

    with patch("app.services.complaint_service.ai_service.analyze_complaint", new_callable=AsyncMock) as mock_analyze, \
         patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:

        mock_analyze.return_value = mock_ai
        mock_query.side_effect = [
            [{"id": str(PWD_DEPT_ID)}],
            [created_record],
            [{"id": str(uuid4())}],
        ]

        req = ComplaintCreate(
            title="Road hole",
            description="Deep depression in the road surface",
            latitude=15.498,
            longitude=73.827,
            category="Roads",
            issue_type="Pothole",
        )

        asyncio.run(service.create_complaint(citizen_user, req))

        complaint_insert_payload = mock_query.call_args_list[1][1]["json_data"]
        assert complaint_insert_payload["ai_summary"] == mock_ai.summary
        print("[PASS] Test 2: AI summary mapped exactly to database payload ai_summary")


def test_3_ai_severity_mapping():
    """Test 3: Correct mapping of AI severity to severity column."""
    print("\n--- Test 3: AI Severity Mapping ---")
    service = ComplaintService()
    cid = uuid4()

    mock_ai = AIAnalysisResponse(
        suggested_title="Water pipe burst",
        category="Water leakage, drainage blockage",
        issue_type="Pipe Burst",
        department="Water & Sewerage Department",
        severity=9,
        is_safety_related=False,
        safety_category=None,
        summary="Severe water main failure flooding roadway.",
        recommended_action="Isolate valve and mobilize emergency pipeline repair.",
        language="English",
    )

    created_record = make_mock_complaint(complaint_id=cid, severity=9, priority="Critical")

    with patch("app.services.complaint_service.ai_service.analyze_complaint", new_callable=AsyncMock) as mock_analyze, \
         patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:

        mock_analyze.return_value = mock_ai
        mock_query.side_effect = [
            [{"id": str(PWD_DEPT_ID)}],
            [created_record],
            [{"id": str(uuid4())}],
        ]

        req = ComplaintCreate(
            title="Water pipe burst",
            description="Water gushing across entire street",
            latitude=15.498,
            longitude=73.827,
            category="Water",
            issue_type="Leakage",
        )

        asyncio.run(service.create_complaint(citizen_user, req))

        complaint_insert_payload = mock_query.call_args_list[1][1]["json_data"]
        assert complaint_insert_payload["severity"] == 9
        print("[PASS] Test 3: AI severity mapped directly to database payload severity")


def test_4_ai_category_mapping():
    """Test 4: Correct mapping of AI category to category column."""
    print("\n--- Test 4: AI Category Mapping ---")
    service = ComplaintService()
    cid = uuid4()

    mock_ai = AIAnalysisResponse(
        suggested_title="Garbage pile up",
        category="Garbage accumulation",
        issue_type="Overflowing Bin",
        department="Sanitation Department",
        severity=4,
        is_safety_related=False,
        safety_category=None,
        summary="Uncollected municipal waste accumulating.",
        recommended_action="Dispatch sanitation collection truck.",
        language="English",
    )

    created_record = make_mock_complaint(complaint_id=cid)

    with patch("app.services.complaint_service.ai_service.analyze_complaint", new_callable=AsyncMock) as mock_analyze, \
         patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:

        mock_analyze.return_value = mock_ai
        mock_query.side_effect = [
            [{"id": str(SANITATION_DEPT_ID)}],
            [created_record],
            [{"id": str(uuid4())}],
        ]

        req = ComplaintCreate(
            title="Trash problem",
            description="Waste not collected for several days",
            latitude=15.498,
            longitude=73.827,
            category="Other",
            issue_type="Trash",
        )

        asyncio.run(service.create_complaint(citizen_user, req))

        complaint_insert_payload = mock_query.call_args_list[1][1]["json_data"]
        assert complaint_insert_payload["category"] == "Garbage accumulation"
        print("[PASS] Test 4: AI category mapped to database payload category")


def test_5_department_uuid_resolved_from_ai_category():
    """Test 5: Department UUID resolved from AI department name via departments table."""
    print("\n--- Test 5: Department UUID Resolution via Departments Table ---")
    service = ComplaintService()
    cid = uuid4()
    dept_uuid = str(uuid4())

    mock_ai = AIAnalysisResponse(
        suggested_title="Streetlight Failure",
        category="Broken streetlights",
        issue_type="Streetlight Outage",
        department="Electrical Department",
        severity=5,
        is_safety_related=False,
        safety_category=None,
        summary="Dark street corner due to failed lighting fixture.",
        recommended_action="Inspect wiring circuit and replace bulb.",
        language="English",
    )

    created_record = make_mock_complaint(complaint_id=cid, department_id=UUID(dept_uuid))

    with patch("app.services.complaint_service.ai_service.analyze_complaint", new_callable=AsyncMock) as mock_analyze, \
         patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:

        mock_analyze.return_value = mock_ai
        mock_query.side_effect = [
            [{"id": dept_uuid}],
            [created_record],
            [{"id": str(uuid4())}],
        ]

        req = ComplaintCreate(
            title="Broken streetlamp",
            description="Dark stretch of street with no light",
            latitude=15.498,
            longitude=73.827,
            category="Lighting",
            issue_type="Streetlight",
        )

        asyncio.run(service.create_complaint(citizen_user, req))

        dept_lookup_call = mock_query.call_args_list[0]
        assert dept_lookup_call[1]["params"]["name"] == "eq.Electrical Department"
        complaint_insert_payload = mock_query.call_args_list[1][1]["json_data"]
        assert complaint_insert_payload["department_id"] == dept_uuid
        print("[PASS] Test 5: Department UUID resolved dynamically via departments table query")


def test_6_unassigned_fallback_when_department_not_found():
    """Test 6: Fallback to unassigned (department_id = None) when AI category does not match any department."""
    print("\n--- Test 6: Fallback to Unassigned When Department Not Found ---")
    service = ComplaintService()
    cid = uuid4()

    mock_ai = AIAnalysisResponse(
        suggested_title="Unknown Civic Issue",
        category="Other",
        issue_type="Other Concern",
        department="Public Works Department",
        severity=3,
        is_safety_related=False,
        safety_category=None,
        summary="Unclassified general civic inquiry.",
        recommended_action="Review civic inquiry for manual department allocation.",
        language="English",
    )

    created_record = make_mock_complaint(complaint_id=cid, department_id=None)

    with patch("app.services.complaint_service.ai_service.analyze_complaint", new_callable=AsyncMock) as mock_analyze, \
         patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:

        mock_analyze.return_value = mock_ai
        mock_query.side_effect = [
            [],               # Empty dept lookup -> no matching department found in database
            [created_record],
            [{"id": str(uuid4())}],
        ]

        req = ComplaintCreate(
            title="Unusual issue",
            description="Strange civic matter needing attention",
            latitude=15.498,
            longitude=73.827,
            category="Other",
            issue_type="Other",
        )

        res = asyncio.run(service.create_complaint(citizen_user, req))

        complaint_insert_payload = mock_query.call_args_list[1][1]["json_data"]
        assert complaint_insert_payload["department_id"] is None
        print("[PASS] Test 6: Fallback to department_id=None succeeds when department not found in database")


def test_7_deterministic_fallback_when_gemini_raises():
    """Test 7: Deterministic fallback when Gemini API / AI service raises an exception."""
    print("\n--- Test 7: Deterministic Fallback on Gemini Service Exception ---")
    service = ComplaintService()
    cid = uuid4()

    created_record = make_mock_complaint(
        complaint_id=cid,
        department_id=None,
        severity=5,
        priority="Medium",
        ai_summary="Complaint description lacks sufficient detail for automated department classification.",
    )

    with patch("app.services.complaint_service.ai_service.analyze_complaint", new_callable=AsyncMock) as mock_analyze, \
         patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:

        mock_analyze.side_effect = RuntimeError("503 Service Unavailable: Gemini API quota exceeded")
        mock_query.side_effect = [
            [created_record],         # 1. Insert complaint (fallback has department=None, so no dept lookup)
            [{"id": str(uuid4())}],   # 2. Insert complaint_updates initial history
        ]

        req = ComplaintCreate(
            title="Civic grievance",
            description="Civic issue submitted while AI service is temporarily down",
            latitude=15.498,
            longitude=73.827,
            category="Roads",
            issue_type="Pothole",
        )

        res = asyncio.run(service.create_complaint(citizen_user, req))

        assert res.id == cid
        complaint_insert_payload = mock_query.call_args_list[0][1]["json_data"]
        assert complaint_insert_payload["status"] == "Submitted"
        assert complaint_insert_payload["ai_summary"] is not None
        assert len(complaint_insert_payload["ai_summary"]) > 0
        print("[PASS] Test 7: Deterministic fallback engaged seamlessly when AI service throws exception")


def test_8_citizen_identity_cannot_be_overwritten():
    """Test 8: Citizen identity (citizen_id) cannot be overwritten by AI output or client body."""
    print("\n--- Test 8: Citizen Identity Protection ---")
    service = ComplaintService()
    cid = uuid4()

    mock_ai = AIAnalysisResponse(
        suggested_title="Damaged Road Surface",
        category="Potholes, damaged roads, footpaths",
        issue_type="Pothole",
        department="Public Works Department",
        severity=5,
        is_safety_related=False,
        safety_category=None,
        summary="Road inspection summary.",
        recommended_action="Inspect and patch road.",
        language="English",
    )

    created_record = make_mock_complaint(complaint_id=cid, citizen_id=CITIZEN_ID)

    with patch("app.services.complaint_service.ai_service.analyze_complaint", new_callable=AsyncMock) as mock_analyze, \
         patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:

        mock_analyze.return_value = mock_ai
        mock_query.side_effect = [
            [{"id": str(PWD_DEPT_ID)}],
            [created_record],
            [{"id": str(uuid4())}],
        ]

        req = ComplaintCreate(
            title="Road hole",
            description="Deep crater",
            latitude=15.498,
            longitude=73.827,
            category="Roads",
            issue_type="Pothole",
        )

        asyncio.run(service.create_complaint(citizen_user, req))

        complaint_insert_payload = mock_query.call_args_list[1][1]["json_data"]
        assert complaint_insert_payload["citizen_id"] == str(CITIZEN_ID)
        assert complaint_insert_payload["citizen_id"] != str(OTHER_CITIZEN_ID)
        print("[PASS] Test 8: citizen_id strictly bounded to authenticated citizen token")


def test_9_safety_union_rule_citizen_safety_preserved():
    """Test 9: Safety union rule: citizen marks safety_related=True, AI returns False -> final True."""
    print("\n--- Test 9: Safety Union Rule (Citizen Safety Intent Preserved) ---")
    service = ComplaintService()
    cid = uuid4()

    mock_ai = AIAnalysisResponse(
        suggested_title="Dark Alleyway",
        category="Broken streetlights",
        issue_type="Light Outage",
        department="Electrical Department",
        severity=4,
        is_safety_related=False,   # AI downplays safety
        safety_category=None,
        summary="Dark pathway report.",
        recommended_action="Inspect lighting fixtures.",
        language="English",
    )

    created_record = make_mock_complaint(complaint_id=cid, safety_related=True)

    with patch("app.services.complaint_service.ai_service.analyze_complaint", new_callable=AsyncMock) as mock_analyze, \
         patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:

        mock_analyze.return_value = mock_ai
        mock_query.side_effect = [
            [{"id": str(PWD_DEPT_ID)}],
            [created_record],
            [{"id": str(uuid4())}],
        ]

        req = ComplaintCreate(
            title="Dark deserted pathway",
            description="Pathway completely dark and dangerous after 8pm",
            latitude=15.498,
            longitude=73.827,
            category="Lighting",
            issue_type="Streetlight",
            safety_related=True,
            safety_category="Lighting issue",
        )

        asyncio.run(service.create_complaint(citizen_user, req))

        complaint_insert_payload = mock_query.call_args_list[1][1]["json_data"]
        assert complaint_insert_payload["safety_related"] is True
        assert complaint_insert_payload["safety_category"] == "Lighting issue"
        print("[PASS] Test 9: Citizen's safety declaration successfully preserved despite AI non-safety classification")


def test_10_safety_union_rule_ai_safety_upgraded():
    """Test 10: Safety union rule: citizen marks safety_related=False, AI returns True -> final True."""
    print("\n--- Test 10: Safety Union Rule (AI Upgrades Unmarked Safety Hazard) ---")
    service = ComplaintService()
    cid = uuid4()

    mock_ai = AIAnalysisResponse(
        suggested_title="Exposed High Voltage Cable",
        category="Broken streetlights",
        issue_type="Live Wire",
        department="Electrical Department",
        severity=9,
        is_safety_related=True,    # AI detects severe hazard
        safety_category="Lighting issue",
        summary="High hazard: Exposed electrical cabling near sidewalk.",
        recommended_action="Emergency cutoff and cordon off hazardous area.",
        language="English",
    )

    created_record = make_mock_complaint(complaint_id=cid, safety_related=True)

    with patch("app.services.complaint_service.ai_service.analyze_complaint", new_callable=AsyncMock) as mock_analyze, \
         patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:

        mock_analyze.return_value = mock_ai
        mock_query.side_effect = [
            [{"id": str(PWD_DEPT_ID)}],
            [created_record],
            [{"id": str(uuid4())}],
        ]

        req = ComplaintCreate(
            title="Wires on the pavement",
            description="Sparking cable hanging down to pedestrian sidewalk level",
            latitude=15.498,
            longitude=73.827,
            category="Lighting",
            issue_type="Cables",
            safety_related=False,  # Citizen did not check the box
            safety_category=None,
        )

        asyncio.run(service.create_complaint(citizen_user, req))

        complaint_insert_payload = mock_query.call_args_list[1][1]["json_data"]
        assert complaint_insert_payload["safety_related"] is True
        assert complaint_insert_payload["safety_category"] == "Lighting issue"
        print("[PASS] Test 10: AI safely upgraded safety_related flag and applied safety_category")


# ==============================================================================
# GROUP 2: PRIORITY CALCULATION (TESTS 11–13)
# ==============================================================================

def test_11_initial_priority_calculation():
    """Test 11: Initial priority calculated from severity and initial report_count=1."""
    print("\n--- Test 11: Initial Priority Calculation Verification ---")
    p9 = priority_service.calculate_priority(severity=9, report_count=1, overdue_bonus=0)
    assert p9 == "Critical"

    p7 = priority_service.calculate_priority(severity=7, report_count=1, overdue_bonus=0)
    assert p7 == "High"

    p4 = priority_service.calculate_priority(severity=4, report_count=1, overdue_bonus=0)
    assert p4 == "Medium"

    p2 = priority_service.calculate_priority(severity=2, report_count=1, overdue_bonus=0)
    assert p2 == "Low"

    print("[PASS] Test 11: Initial priority formulas conform to PRD specification thresholds")


def test_12_priority_recalculated_on_duplicate_linking():
    """Test 12: Priority recalculated when report_count increases via duplicate linking."""
    print("\n--- Test 12: Priority Recalculation on Report Count Increase ---")
    initial_p = priority_service.calculate_priority(severity=7, report_count=1, overdue_bonus=0)
    assert initial_p == "High"

    p_count_2 = priority_service.calculate_priority(severity=7, report_count=2, overdue_bonus=0)
    assert p_count_2 == "High"

    p_count_3 = priority_service.calculate_priority(severity=7, report_count=3, overdue_bonus=0)
    assert p_count_3 == "Critical"

    print("[PASS] Test 12: Escalation to Critical verified when report_count reaches threshold 80")


def test_13_explicit_official_priority_override_preserved():
    """Test 13: Explicit official priority override preserved during status update."""
    print("\n--- Test 13: Explicit Official Priority Override Preserved ---")
    service = ComplaintService()
    cid = uuid4()
    mock_record = make_mock_complaint(cid, priority="Medium", status="Submitted")
    updated_record = dict(mock_record)
    updated_record["status"] = "Under Review"
    updated_record["priority"] = "Critical"

    with patch("app.services.complaint_service.duplicate_service.find_duplicates", new_callable=AsyncMock) as mock_find, \
         patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:
        mock_find.return_value = []
        mock_query.side_effect = [
            [mock_record],       # 1. Fetch current record (in get_complaint_by_id)
            [],                  # 2. History timeline query (in get_complaint_by_id)
            [updated_record],    # 3. Apply PATCH (in _execute_official_status_update)
            [{"id": str(uuid4())}],  # 4. Record history (in _execute_official_status_update)
        ]

        req = OfficialStatusUpdate(
            status="Under Review",
            remarks="Ministerial inquiry: Escalating priority to Critical",
            priority="Critical",
        )

        res = asyncio.run(service.update_status_as_official(cid, pwd_official, req))

        patch_payload = mock_query.call_args_list[2][1]["json_data"]
        assert patch_payload["priority"] == "Critical"
        assert res.priority == "Critical"
        print("[PASS] Test 13: Official explicit priority override preserved in database update")


# ==============================================================================
# GROUP 3: ADVISORY DUPLICATE DETECTION (TESTS 14–18)
# ==============================================================================

def test_14_advisory_duplicates_returned_for_official():
    """Test 14: Advisory duplicate candidates returned in GET /complaints/{id} for authorized official."""
    print("\n--- Test 14: Advisory Duplicate Candidates Returned for Official ---")
    service = ComplaintService()
    cid = uuid4()
    dupe_id_1 = str(uuid4())
    dupe_id_2 = str(uuid4())

    mock_record = make_mock_complaint(cid, status="Submitted", safety_related=False)
    # Member 3 duplicate_service format uses 'complaint_id'
    mock_dupes = [
        {"complaint_id": dupe_id_1, "title": "Pothole nearby", "distance_meters": 30.5, "report_count": 1},
        {"complaint_id": dupe_id_2, "title": "Crater down road", "distance_meters": 55.0, "report_count": 2},
    ]

    with patch("app.services.complaint_service.duplicate_service.find_duplicates", new_callable=AsyncMock) as mock_find, \
         patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:

        mock_find.return_value = mock_dupes
        mock_query.side_effect = [
            [mock_record],       # 1. Fetch complaint
            [],                  # 2. Updates timeline
            [],                  # 3. Secondary safety check for candidates -> none are safety
        ]

        res = asyncio.run(service.get_complaint_by_id(cid, pwd_official))

        assert len(res.duplicates) == 2
        assert res.duplicates[0]["complaint_id"] == dupe_id_1
        assert res.duplicates[1]["complaint_id"] == dupe_id_2
        print("[PASS] Test 14: Advisory duplicates successfully returned in ComplaintDetailResponse")


def test_15_ordinary_official_filtered_from_safety_duplicates():
    """Test 15: Ordinary official blocked from seeing safety-flagged candidates in duplicates list."""
    print("\n--- Test 15: Safety-Flagged Duplicates Filtered for Ordinary Officials ---")
    service = ComplaintService()
    cid = uuid4()
    safe_dupe_id = str(uuid4())
    hazardous_dupe_id = str(uuid4())

    mock_record = make_mock_complaint(cid, status="Submitted", safety_related=False)
    mock_dupes = [
        {"complaint_id": safe_dupe_id, "title": "Pothole nearby", "distance_meters": 25.0},
        {"complaint_id": hazardous_dupe_id, "title": "Cave-in with electrical line", "distance_meters": 32.0},
    ]

    with patch("app.services.complaint_service.duplicate_service.find_duplicates", new_callable=AsyncMock) as mock_find, \
         patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:

        mock_find.return_value = mock_dupes
        mock_query.side_effect = [
            [mock_record],       # 1. Fetch complaint
            [],                  # 2. Updates timeline
            [{"id": hazardous_dupe_id}],  # 3. Safety lookup reports hazardous_dupe_id is safety_related
        ]

        # pwd_official is NOT a safety officer
        res = asyncio.run(service.get_complaint_by_id(cid, pwd_official))

        assert len(res.duplicates) == 1
        assert res.duplicates[0]["complaint_id"] == safe_dupe_id
        assert all(d.get("complaint_id") != hazardous_dupe_id for d in res.duplicates)
        print("[PASS] Test 15: Hazardous safety duplicate strictly filtered from ordinary official response")


def test_16_safety_officer_can_see_safety_duplicates():
    """Test 16: Safety officer can see safety-flagged candidates in duplicates list."""
    print("\n--- Test 16: Safety Officer Can See Safety-Flagged Duplicates ---")
    service = ComplaintService()
    cid = uuid4()
    safe_dupe_id = str(uuid4())
    hazardous_dupe_id = str(uuid4())

    mock_record = make_mock_complaint(cid, status="Submitted", safety_related=True)
    mock_dupes = [
        {"complaint_id": safe_dupe_id, "title": "Pothole nearby", "distance_meters": 25.0},
        {"complaint_id": hazardous_dupe_id, "title": "Cave-in with electrical line", "distance_meters": 32.0},
    ]

    with patch("app.services.complaint_service.duplicate_service.find_duplicates", new_callable=AsyncMock) as mock_find, \
         patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:

        mock_find.return_value = mock_dupes
        mock_query.side_effect = [
            [mock_record],       # 1. Fetch complaint
            [],                  # 2. Updates timeline
        ]

        # safety_officer has is_safety_officer=True
        res = asyncio.run(service.get_complaint_by_id(cid, safety_officer))

        assert len(res.duplicates) == 2
        candidate_ids = {d.get("complaint_id") for d in res.duplicates}
        assert safe_dupe_id in candidate_ids
        assert hazardous_dupe_id in candidate_ids
        print("[PASS] Test 16: Designated safety officer receives full duplicate list including safety candidates")


def test_17_citizen_blocked_from_duplicates():
    """Test 17: Citizen does NOT receive duplicates field / duplicates list is empty."""
    print("\n--- Test 17: Citizen Blocked from Duplicate Insights ---")
    service = ComplaintService()
    cid = uuid4()
    mock_record = make_mock_complaint(cid, citizen_id=CITIZEN_ID, status="Submitted")

    with patch("app.services.complaint_service.duplicate_service.find_duplicates", new_callable=AsyncMock) as mock_find, \
         patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:

        mock_query.side_effect = [
            [mock_record],       # 1. Fetch complaint
            [],                  # 2. Updates timeline
        ]

        res = asyncio.run(service.get_complaint_by_id(cid, citizen_user))

        mock_find.assert_not_called()
        assert res.duplicates == []
        print("[PASS] Test 17: Citizen receives empty duplicates list; duplicate_service was not invoked")


def test_18_advisory_duplicate_detection_strictly_read_only():
    """Test 18: Advisory duplicate detection is strictly read-only (no database writes)."""
    print("\n--- Test 18: Advisory Duplicate Detection Strictly Read-Only ---")
    service = ComplaintService()
    cid = uuid4()
    mock_record = make_mock_complaint(cid, status="Submitted")
    mock_dupes = [{"complaint_id": str(uuid4()), "title": "Pothole nearby", "distance_meters": 20.0}]

    with patch("app.services.complaint_service.duplicate_service.find_duplicates", new_callable=AsyncMock) as mock_find, \
         patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:

        mock_find.return_value = mock_dupes
        mock_query.side_effect = [
            [mock_record],       # 1. Fetch complaint
            [],                  # 2. Updates timeline
            [],                  # 3. Safety check
        ]

        asyncio.run(service.get_complaint_by_id(cid, pwd_official))

        for call_item in mock_query.call_args_list:
            method = call_item[1].get("method", "GET")
            assert method == "GET", f"Illegal non-read operation detected: {method}"

        print("[PASS] Test 18: Zero mutation queries executed during advisory duplicate retrieval")


# ==============================================================================
# GROUP 4: OFFICIAL DUPLICATE LINKING (TESTS 19–25)
# ==============================================================================

def test_19_authorized_official_duplicate_linking():
    """Test 19: Authorized official links duplicate complaint successfully."""
    print("\n--- Test 19: Authorized Official Duplicate Linking ---")
    service = ComplaintService()
    child_id = uuid4()
    master_id = uuid4()

    child_record = make_mock_complaint(child_id, department_id=PWD_DEPT_ID, report_count=1)
    master_record = make_mock_complaint(master_id, department_id=PWD_DEPT_ID, report_count=1, severity=7, priority="High")

    updated_child = dict(child_record)
    updated_child["master_incident_id"] = str(master_id)

    updated_master = dict(master_record)
    updated_master["report_count"] = 2
    updated_master["priority"] = "High"

    with patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:
        mock_query.side_effect = [
            [child_record],      # 1. Fetch child
            [master_record],     # 2. Fetch master
            [],                  # 3. Check if child is already a master with existing children
            [updated_child],     # 4. PATCH child (set master_incident_id)
            [updated_master],    # 5. PATCH master (increment count, recalculate priority)
            [{"id": str(uuid4())}],  # 6. POST child history update
            [{"id": str(uuid4())}],  # 7. POST master history update
        ]

        res = asyncio.run(service.link_duplicate_complaint(child_id, master_id, pwd_official))

        assert res.id == child_id
        assert res.master_incident_id == master_id

        child_patch = mock_query.call_args_list[3][1]["json_data"]
        assert child_patch["master_incident_id"] == str(master_id)

        master_patch = mock_query.call_args_list[4][1]["json_data"]
        assert master_patch["report_count"] == 2
        print("[PASS] Test 19: Authorized duplicate link established with child and master mutations")


def test_20_cross_department_duplicate_linking_rejected():
    """Test 20: Cross-department duplicate linking rejected (HTTP 400 or 403)."""
    print("\n--- Test 20: Cross-Department Duplicate Linking Rejected ---")
    service = ComplaintService()
    child_id = uuid4()
    master_id = uuid4()

    child_record = make_mock_complaint(child_id, department_id=PWD_DEPT_ID)
    master_record = make_mock_complaint(master_id, department_id=SANITATION_DEPT_ID)

    with patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:
        mock_query.side_effect = [
            [child_record],
            [master_record],
        ]

        try:
            asyncio.run(service.link_duplicate_complaint(child_id, master_id, pwd_official))
            assert False, "Expected HTTPException"
        except HTTPException as exc:
            assert exc.status_code in (400, 403)
            print(f"[PASS] Test 20: Cross-department linking rejected with HTTP {exc.status_code}: {exc.detail}")


def test_21_self_linking_rejected():
    """Test 21: Self-linking rejected (HTTP 400)."""
    print("\n--- Test 21: Self-Linking Rejection ---")
    service = ComplaintService()
    same_id = uuid4()

    try:
        asyncio.run(service.link_duplicate_complaint(same_id, same_id, pwd_official))
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "itself" in exc.detail.lower()
        print(f"[PASS] Test 21: Self-linking rejected with HTTP 400: {exc.detail}")


def test_22_child_already_linked_rejected():
    """Test 22: Child complaint that is already a child rejected from being linked again (HTTP 400)."""
    print("\n--- Test 22: Already-Linked Child Duplicate Rejected ---")
    service = ComplaintService()
    child_id = uuid4()
    master_id = uuid4()
    existing_master_id = uuid4()

    child_record = make_mock_complaint(child_id, department_id=PWD_DEPT_ID, master_incident_id=existing_master_id)
    master_record = make_mock_complaint(master_id, department_id=PWD_DEPT_ID)

    with patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:
        mock_query.side_effect = [
            [child_record],
            [master_record],
            [],
        ]

        try:
            asyncio.run(service.link_duplicate_complaint(child_id, master_id, pwd_official))
            assert False, "Expected HTTPException"
        except HTTPException as exc:
            assert exc.status_code == 400
            assert "already linked" in exc.detail.lower()
            print(f"[PASS] Test 22: Already-linked child rejected with HTTP 400: {exc.detail}")


def test_23_master_cannot_be_child_multi_tier_rejected():
    """Test 23: Master complaint cannot be linked as a child to another complaint (no multi-tier hierarchy) (HTTP 400)."""
    print("\n--- Test 23: Multi-Tier Hierarchy Rejection ---")
    service = ComplaintService()
    child_id = uuid4()
    master_id = uuid4()

    child_record = make_mock_complaint(child_id, department_id=PWD_DEPT_ID)
    master_as_child_record = make_mock_complaint(master_id, department_id=PWD_DEPT_ID, master_incident_id=uuid4())

    with patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:
        mock_query.side_effect = [
            [child_record],
            [master_as_child_record],
        ]

        try:
            asyncio.run(service.link_duplicate_complaint(child_id, master_id, pwd_official))
            assert False, "Expected HTTPException"
        except HTTPException as exc:
            assert exc.status_code == 400
            assert "already a duplicate child" in exc.detail.lower()

    clean_master_record = make_mock_complaint(master_id, department_id=PWD_DEPT_ID)
    with patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:
        mock_query.side_effect = [
            [child_record],
            [clean_master_record],
            [{"id": str(uuid4())}],   # existing children query returns non-empty!
        ]

        try:
            asyncio.run(service.link_duplicate_complaint(child_id, master_id, pwd_official))
            assert False, "Expected HTTPException"
        except HTTPException as exc:
            assert exc.status_code == 400
            assert "already a master incident" in exc.detail.lower()

    print("[PASS] Test 23: Multi-tier hierarchies rejected in both directions (HTTP 400)")


def test_24_master_report_count_and_priority_recalculated():
    """Test 24: Master report_count incremented and priority recalculated upon successful link."""
    print("\n--- Test 24: Master Report Count & Priority Recalculated ---")
    service = ComplaintService()
    child_id = uuid4()
    master_id = uuid4()

    master_record = make_mock_complaint(master_id, department_id=PWD_DEPT_ID, severity=6, report_count=4, priority="High")
    child_record = make_mock_complaint(child_id, department_id=PWD_DEPT_ID)

    updated_child = dict(child_record)
    updated_child["master_incident_id"] = str(master_id)

    updated_master = dict(master_record)
    updated_master["report_count"] = 5
    updated_master["priority"] = "Critical"

    with patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:
        mock_query.side_effect = [
            [child_record],
            [master_record],
            [],
            [updated_child],
            [updated_master],
            [{"id": str(uuid4())}],
            [{"id": str(uuid4())}],
        ]

        asyncio.run(service.link_duplicate_complaint(child_id, master_id, pwd_official))

        master_patch = mock_query.call_args_list[4][1]["json_data"]
        assert master_patch["report_count"] == 5
        assert master_patch["priority"] == "Critical"
        print("[PASS] Test 24: Master report_count incremented to 5 and priority escalated to Critical")


def test_25_timeline_updates_logged_for_both_child_and_master():
    """Test 25: Chronological update entries recorded for BOTH child and master complaints."""
    print("\n--- Test 25: Chronological Update Entries for Child and Master ---")
    service = ComplaintService()
    child_id = uuid4()
    master_id = uuid4()

    child_record = make_mock_complaint(child_id, department_id=PWD_DEPT_ID, status="Assigned")
    master_record = make_mock_complaint(master_id, department_id=PWD_DEPT_ID, status="In Progress", report_count=2, severity=7)

    updated_child = dict(child_record)
    updated_child["master_incident_id"] = str(master_id)

    updated_master = dict(master_record)
    updated_master["report_count"] = 3
    updated_master["priority"] = "Critical"

    with patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:
        mock_query.side_effect = [
            [child_record],
            [master_record],
            [],
            [updated_child],
            [updated_master],
            [{"id": str(uuid4())}],   # Call 5: Child history POST
            [{"id": str(uuid4())}],   # Call 6: Master history POST
        ]

        asyncio.run(service.link_duplicate_complaint(child_id, master_id, pwd_official))

        child_history_payload = mock_query.call_args_list[5][1]["json_data"]
        assert child_history_payload["complaint_id"] == str(child_id)
        assert child_history_payload["actor_id"] == str(PWD_OFFICIAL_ID)
        assert child_history_payload["status"] == "Assigned"
        assert str(master_id) in child_history_payload["remarks"]

        master_history_payload = mock_query.call_args_list[6][1]["json_data"]
        assert master_history_payload["complaint_id"] == str(master_id)
        assert master_history_payload["actor_id"] == str(PWD_OFFICIAL_ID)
        assert master_history_payload["status"] == "In Progress"
        assert "Community report count incremented to 3" in master_history_payload["remarks"]
        assert str(child_id) in master_history_payload["remarks"]

        print("[PASS] Test 25: Both child and master complaint_updates records logged with full context")


# ==============================================================================
# GROUP 5: HARDENED ROLLBACK, CANDIDATE KEYS & CONCURRENCY (TESTS 26–38)
# ==============================================================================

def test_26_duplicate_candidate_ids_using_complaint_id():
    """Test 26: Duplicate candidate IDs using Member 3's 'complaint_id' key."""
    print("\n--- Test 26: Duplicate Candidate Key Matching (complaint_id) ---")
    service = ComplaintService()
    cid = uuid4()
    candidate_uuid = str(uuid4())

    mock_record = make_mock_complaint(cid, status="Submitted", safety_related=False)
    mock_candidates = [
        {"complaint_id": candidate_uuid, "title": "Pothole nearby", "distance_meters": 15.0}
    ]

    with patch("app.services.complaint_service.duplicate_service.find_duplicates", new_callable=AsyncMock) as mock_find, \
         patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:
        mock_find.return_value = mock_candidates
        mock_query.side_effect = [
            [mock_record],
            [],
            [],  # Secondary safety check returns no safety records
        ]

        res = asyncio.run(service.get_complaint_by_id(cid, pwd_official))
        assert len(res.duplicates) == 1
        assert res.duplicates[0]["complaint_id"] == candidate_uuid
        print("[PASS] Test 26: Candidate matched successfully using Member 3 complaint_id key")


def test_27_backward_compatibility_with_id_key():
    """Test 27: Backward compatibility with legacy/alternative 'id' candidate key."""
    print("\n--- Test 27: Backward Compatibility with 'id' Key ---")
    service = ComplaintService()
    cid = uuid4()
    candidate_uuid = str(uuid4())

    mock_record = make_mock_complaint(cid, status="Submitted", safety_related=False)
    mock_candidates = [
        {"id": candidate_uuid, "title": "Legacy candidate", "distance_meters": 20.0}
    ]

    with patch("app.services.complaint_service.duplicate_service.find_duplicates", new_callable=AsyncMock) as mock_find, \
         patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:
        mock_find.return_value = mock_candidates
        mock_query.side_effect = [
            [mock_record],
            [],
            [],
        ]

        res = asyncio.run(service.get_complaint_by_id(cid, pwd_official))
        assert len(res.duplicates) == 1
        assert res.duplicates[0]["id"] == candidate_uuid
        print("[PASS] Test 27: Legacy candidates with 'id' key preserved seamlessly")


def test_28_ordinary_official_safety_filtering_member3_shape():
    """Test 28: Ordinary official safety filtering using Member 3 real output shape."""
    print("\n--- Test 28: Safety Filtering with Authentic Member 3 Output Shape ---")
    service = ComplaintService()
    cid = uuid4()
    safe_cid = str(uuid4())
    safety_cid = str(uuid4())

    mock_record = make_mock_complaint(cid, status="Submitted", safety_related=False)
    mock_candidates = [
        {"complaint_id": safe_cid, "title": "Pothole nearby", "distance_meters": 22.0},
        {"complaint_id": safety_cid, "title": "Exposed high voltage wire", "distance_meters": 30.0},
    ]

    with patch("app.services.complaint_service.duplicate_service.find_duplicates", new_callable=AsyncMock) as mock_find, \
         patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:
        mock_find.return_value = mock_candidates
        mock_query.side_effect = [
            [mock_record],
            [],
            [{"id": safety_cid}],  # safety query reports safety_cid is safety-related
        ]

        # pwd_official is an ordinary official
        res = asyncio.run(service.get_complaint_by_id(cid, pwd_official))
        assert len(res.duplicates) == 1
        assert res.duplicates[0]["complaint_id"] == safe_cid
        assert all(d.get("complaint_id") != safety_cid for d in res.duplicates)
        print("[PASS] Test 28: Ordinary official successfully filtered from safety candidate using complaint_id")


def test_29_master_update_unsuccessful_triggers_child_rollback():
    """Test 29: Master update returning unsuccessful result (empty list) triggers child rollback."""
    print("\n--- Test 29: Master Update Unsuccessful Triggers Child Rollback ---")
    service = ComplaintService()
    child_id = uuid4()
    master_id = uuid4()

    child_record = make_mock_complaint(child_id, department_id=PWD_DEPT_ID)
    master_record = make_mock_complaint(master_id, department_id=PWD_DEPT_ID)

    with patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:
        mock_query.side_effect = [
            [child_record],     # 1. Fetch child
            [master_record],    # 2. Fetch master
            [],                 # 3. Check existing children
            [{"id": str(child_id), "master_incident_id": str(master_id)}],  # 4. Child PATCH succeeds
            [],                 # 5. Master PATCH returns empty list (failure)
            [{"id": str(child_id), "master_incident_id": None}],            # 6. Compensating rollback on child
        ]

        try:
            asyncio.run(service.link_duplicate_complaint(child_id, master_id, pwd_official))
            assert False, "Expected HTTPException 500"
        except HTTPException as exc:
            assert exc.status_code == 500
            assert "Automatic compensating rollback completed successfully" in exc.detail
            # Check call 6 rolled back child's master_incident_id to None
            child_rollback_call = mock_query.call_args_list[5]
            assert child_rollback_call[1]["json_data"]["master_incident_id"] is None
            print("[PASS] Test 29: Child rollback executed after empty master update response")


def test_30_master_update_transport_exception_triggers_child_rollback():
    """Test 30: Master update raising transport exception triggers child rollback."""
    print("\n--- Test 30: Master Update Transport Exception Triggers Child Rollback ---")
    service = ComplaintService()
    child_id = uuid4()
    master_id = uuid4()

    child_record = make_mock_complaint(child_id, department_id=PWD_DEPT_ID)
    master_record = make_mock_complaint(master_id, department_id=PWD_DEPT_ID)

    with patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:
        mock_query.side_effect = [
            [child_record],
            [master_record],
            [],
            [{"id": str(child_id), "master_incident_id": str(master_id)}],  # Child PATCH succeeds
            RuntimeError("Network connection reset during master PATCH"),    # Master PATCH fails with exception
            [{"id": str(child_id), "master_incident_id": None}],            # Compensating rollback on child
        ]

        try:
            asyncio.run(service.link_duplicate_complaint(child_id, master_id, pwd_official))
            assert False, "Expected HTTPException 500"
        except HTTPException as exc:
            assert exc.status_code == 500
            assert "Automatic compensating rollback completed successfully" in exc.detail
            child_rollback_call = mock_query.call_args_list[5]
            assert child_rollback_call[1]["json_data"]["master_incident_id"] is None
            print("[PASS] Test 30: Child rollback executed after master transport exception")


def test_31_child_history_failure_triggers_compensating_rollback():
    """Test 31: Child history insertion failure triggers rollback of both master and child complaints."""
    print("\n--- Test 31: Child History Failure Triggers Rollback of Master and Child ---")
    service = ComplaintService()
    child_id = uuid4()
    master_id = uuid4()

    child_record = make_mock_complaint(child_id, department_id=PWD_DEPT_ID)
    master_record = make_mock_complaint(master_id, department_id=PWD_DEPT_ID, report_count=1, priority="Medium")

    with patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:
        mock_query.side_effect = [
            [child_record],     # 1. Fetch child
            [master_record],    # 2. Fetch master
            [],                 # 3. Check children
            [{"id": str(child_id), "master_incident_id": str(master_id)}],  # 4. Child PATCH succeeds
            [{"id": str(master_id), "report_count": 2, "priority": "High"}], # 5. Master PATCH succeeds
            RuntimeError("DB history table locked"),                         # 6. Child history fails
            [{"id": str(master_id)}],                                        # 7. Rollback master (count=1, priority=Medium)
            [{"id": str(child_id)}],                                         # 8. Rollback child (master_incident_id=None)
        ]

        try:
            asyncio.run(service.link_duplicate_complaint(child_id, master_id, pwd_official))
            assert False, "Expected HTTPException 500"
        except HTTPException as exc:
            assert exc.status_code == 500
            assert "child history logging" in exc.detail
            assert "Automatic compensating rollback completed successfully" in exc.detail

            # Verify master was rolled back to report_count=1, priority=Medium
            master_rb = mock_query.call_args_list[6][1]["json_data"]
            assert master_rb["report_count"] == 1
            assert master_rb["priority"] == "Medium"

            # Verify child was rolled back to master_incident_id=None
            child_rb = mock_query.call_args_list[7][1]["json_data"]
            assert child_rb["master_incident_id"] is None
            print("[PASS] Test 31: Master and child both restored after child history failure")


def test_32_master_history_failure_triggers_compensating_rollback():
    """Test 32: Master history failure triggers deletion of child history and rollback of complaints."""
    print("\n--- Test 32: Master History Failure Triggers Child History Deletion & Rollback ---")
    service = ComplaintService()
    child_id = uuid4()
    master_id = uuid4()
    created_ch_id = str(uuid4())

    child_record = make_mock_complaint(child_id, department_id=PWD_DEPT_ID)
    master_record = make_mock_complaint(master_id, department_id=PWD_DEPT_ID, report_count=2, priority="Medium")

    with patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:
        mock_query.side_effect = [
            [child_record],
            [master_record],
            [],
            [{"id": str(child_id), "master_incident_id": str(master_id)}],  # Child PATCH
            [{"id": str(master_id), "report_count": 3, "priority": "High"}], # Master PATCH
            [{"id": created_ch_id}],                                         # Child history POST succeeds!
            RuntimeError("Network drop during master history POST"),         # Master history POST fails
            [{"id": created_ch_id}],                                         # 1. Rollback: DELETE child history
            [{"id": str(master_id)}],                                        # 2. Rollback: Restore master
            [{"id": str(child_id)}],                                         # 3. Rollback: Restore child
        ]

        try:
            asyncio.run(service.link_duplicate_complaint(child_id, master_id, pwd_official))
            assert False, "Expected HTTPException 500"
        except HTTPException as exc:
            assert exc.status_code == 500
            assert "master history logging" in exc.detail
            assert "Automatic compensating rollback completed successfully" in exc.detail

            # Verify child history was deleted by exact ID (Call index 7: 0=get_child, 1=get_master, 2=get_children, 3=patch_child, 4=patch_master, 5=post_child_hist, 6=post_master_hist_failed, 7=delete_child_hist)
            del_call = mock_query.call_args_list[7]
            assert del_call[1]["method"] == "DELETE"
            assert del_call[1]["params"]["id"] == f"eq.{created_ch_id}"
            print("[PASS] Test 32: Child history deleted and complaints rolled back after master history failure")


def test_33_rollback_restores_previous_master_count_and_priority():
    """Test 33: Rollback restores exact previous master count and priority."""
    print("\n--- Test 33: Exact Previous Master Count & Priority Restoration ---")
    service = ComplaintService()
    child_id = uuid4()
    master_id = uuid4()

    # Master originally has count=4, priority="Critical"
    child_record = make_mock_complaint(child_id, department_id=PWD_DEPT_ID)
    master_record = make_mock_complaint(master_id, department_id=PWD_DEPT_ID, report_count=4, priority="Critical")

    with patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:
        mock_query.side_effect = [
            [child_record],
            [master_record],
            [],
            [{"id": str(child_id), "master_incident_id": str(master_id)}],
            [{"id": str(master_id), "report_count": 5, "priority": "Critical"}],
            RuntimeError("History failure"),
            [{"id": str(master_id)}],  # Master rollback
            [{"id": str(child_id)}],   # Child rollback
        ]

        try:
            asyncio.run(service.link_duplicate_complaint(child_id, master_id, pwd_official))
            assert False, "Expected HTTPException"
        except HTTPException:
            # Call index 6: 0=get_c, 1=get_m, 2=get_children, 3=patch_c, 4=patch_m, 5=post_ch_fail, 6=rollback_m, 7=rollback_c
            master_rb_call = mock_query.call_args_list[6]
            assert master_rb_call[1]["json_data"]["report_count"] == 4
            assert master_rb_call[1]["json_data"]["priority"] == "Critical"
            print("[PASS] Test 33: Exact prior count 4 and priority 'Critical' restored on master")


def test_34_only_current_operation_history_is_removed():
    """Test 34: Only history entries belonging to the current operation are removed during rollback."""
    print("\n--- Test 34: Isolated History Removal During Rollback ---")
    service = ComplaintService()
    child_id = uuid4()
    master_id = uuid4()
    current_op_hist_id = str(uuid4())

    child_record = make_mock_complaint(child_id, department_id=PWD_DEPT_ID)
    master_record = make_mock_complaint(master_id, department_id=PWD_DEPT_ID)

    with patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:
        mock_query.side_effect = [
            [child_record],
            [master_record],
            [],
            [{"id": str(child_id), "master_incident_id": str(master_id)}],
            [{"id": str(master_id), "report_count": 2, "priority": "High"}],
            [{"id": current_op_hist_id}],
            RuntimeError("Master history failure"),
            [{"id": current_op_hist_id}],  # DELETE child history
            [{"id": str(master_id)}],
            [{"id": str(child_id)}],
        ]

        try:
            asyncio.run(service.link_duplicate_complaint(child_id, master_id, pwd_official))
            assert False, "Expected HTTPException"
        except HTTPException:
            # Call index 7: DELETE child history
            del_call = mock_query.call_args_list[7]
            assert del_call[1]["params"] == {"id": f"eq.{current_op_hist_id}"}
            print("[PASS] Test 34: Targeted history deletion verified by exact primary key")


def test_35_rollback_failure_logged_and_not_falsely_reported():
    """Test 35: Rollback failure is logged and not falsely reported as successful."""
    print("\n--- Test 35: Rollback Failure Reporting ---")
    service = ComplaintService()
    child_id = uuid4()
    master_id = uuid4()

    child_record = make_mock_complaint(child_id, department_id=PWD_DEPT_ID)
    master_record = make_mock_complaint(master_id, department_id=PWD_DEPT_ID)

    with patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:
        mock_query.side_effect = [
            [child_record],
            [master_record],
            [],
            [{"id": str(child_id), "master_incident_id": str(master_id)}],
            [{"id": str(master_id), "report_count": 2, "priority": "High"}],
            RuntimeError("History failure"),
            RuntimeError("Master rollback database timeout!"), # Rollback itself fails!
            RuntimeError("Child rollback database timeout!"),  # Rollback itself fails!
        ]

        try:
            asyncio.run(service.link_duplicate_complaint(child_id, master_id, pwd_official))
            assert False, "Expected HTTPException"
        except HTTPException as exc:
            assert exc.status_code == 500
            assert "Attention required: compensating rollback could not be fully completed" in exc.detail
            print("[PASS] Test 35: Rollback failure reported accurately without false success claims")


def test_36_concurrent_duplicate_links_preserve_both_increments():
    """Test 36: Two concurrent child links to the same master preserve both count increments."""
    print("\n--- Test 36: Concurrent Duplicate Links Serialization ---")
    service = ComplaintService()
    master_id = uuid4()
    child1_id = uuid4()
    child2_id = uuid4()

    # Shared mutable state to simulate real database persistence across concurrent operations
    master_state = {
        "id": str(master_id),
        "citizen_id": str(CITIZEN_ID),
        "title": "Master Incident",
        "description": "Pothole cluster",
        "category": "Potholes, damaged roads, footpaths",
        "issue_type": "Pothole",
        "department_id": str(PWD_DEPT_ID),
        "severity": 7,
        "priority": "High",
        "status": "Submitted",
        "report_count": 1,
        "master_incident_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    async def mock_db(table, method="GET", params=None, json_data=None):
        await asyncio.sleep(0.01)  # Context switch opportunity for race condition simulation
        if table == "complaints":
            if method == "GET":
                cid = params.get("id", "").replace("eq.", "")
                if cid == str(master_id):
                    return [dict(master_state)]
                elif cid == str(child1_id):
                    return [make_mock_complaint(child1_id, department_id=PWD_DEPT_ID)]
                elif cid == str(child2_id):
                    return [make_mock_complaint(child2_id, department_id=PWD_DEPT_ID)]
                elif params.get("master_incident_id"):
                    return []
            elif method == "PATCH":
                cid = params.get("id", "").replace("eq.", "")
                if cid == str(master_id):
                    master_state.update(json_data)
                    return [dict(master_state)]
                elif cid in (str(child1_id), str(child2_id)):
                    rec = make_mock_complaint(UUID(cid), department_id=PWD_DEPT_ID)
                    rec.update(json_data)
                    return [rec]
        elif table == "complaint_updates":
            return [{"id": str(uuid4())}]
        return []

    with patch("app.services.complaint_service.supabase_service.rest_query", side_effect=mock_db):
        async def run_concurrent():
            # Launch two link operations simultaneously against the same master
            t1 = service.link_duplicate_complaint(child1_id, master_id, pwd_official)
            t2 = service.link_duplicate_complaint(child2_id, master_id, pwd_official)
            return await asyncio.gather(t1, t2)

        results = asyncio.run(run_concurrent())
        assert len(results) == 2
        # Final report_count must be 1 + 2 = 3 (neither increment was lost!)
        assert master_state["report_count"] == 3
        # Priority for severity 7 with count 3: (7*10) + ((3-1)*5) = 80 -> Critical!
        assert master_state["priority"] == "Critical"
        print("[PASS] Test 36: Both concurrent increments preserved via in-memory master lock (count=3, Critical)")


def test_37_failed_operation_releases_lock_safely():
    """Test 37: A failed operation releases its lock safely without hanging future requests."""
    print("\n--- Test 37: Lock Safe Release on Error ---")
    service = ComplaintService()
    master_id = uuid4()
    child1_id = uuid4()
    child2_id = uuid4()

    child1_record = make_mock_complaint(child1_id, department_id=PWD_DEPT_ID)
    child2_record = make_mock_complaint(child2_id, department_id=PWD_DEPT_ID)
    master_record = make_mock_complaint(master_id, department_id=PWD_DEPT_ID)

    # 1. Operation 1 fails and raises exception
    with patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:
        mock_query.side_effect = [
            [child1_record],
            [master_record],
            [],
            RuntimeError("Simulated failure during child update"),
        ]
        try:
            asyncio.run(service.link_duplicate_complaint(child1_id, master_id, pwd_official))
            assert False, "Expected failure"
        except HTTPException:
            pass

    # 2. Operation 2 on the SAME master immediately afterwards must acquire lock and succeed
    updated_child2 = dict(child2_record)
    updated_child2["master_incident_id"] = str(master_id)
    updated_master = dict(master_record)
    updated_master["report_count"] = 2
    updated_master["priority"] = "High"

    with patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:
        mock_query.side_effect = [
            [child2_record],
            [master_record],
            [],
            [updated_child2],
            [updated_master],
            [{"id": str(uuid4())}],
            [{"id": str(uuid4())}],
        ]

        res = asyncio.run(service.link_duplicate_complaint(child2_id, master_id, pwd_official))
        assert res.id == child2_id
        assert res.master_incident_id == master_id
        print("[PASS] Test 37: Subsequent operation acquired lock and completed after prior failure")


def test_38_existing_authorization_and_lifecycle_tests():
    """Test 38: Existing duplicate-linking authorization and lifecycle tests still pass."""
    print("\n--- Test 38: Authorization & Lifecycle Boundary Preservations ---")
    service = ComplaintService()
    child_id = uuid4()
    master_id = uuid4()

    # 1. Non-official blocked with HTTP 403
    try:
        asyncio.run(service.link_duplicate_complaint(child_id, master_id, citizen_user))
        assert False, "Expected 403"
    except HTTPException as exc:
        assert exc.status_code == 403

    # 2. Worker blocked with HTTP 403
    try:
        asyncio.run(service.link_duplicate_complaint(child_id, master_id, worker_user))
        assert False, "Expected 403"
    except HTTPException as exc:
        assert exc.status_code == 403

    # 3. Safety complaint blocked for ordinary official
    child_safety = make_mock_complaint(child_id, safety_related=True)
    master_clean = make_mock_complaint(master_id, safety_related=False)
    with patch("app.services.complaint_service.supabase_service.rest_query", new_callable=AsyncMock) as mock_query:
        mock_query.side_effect = [
            [child_safety],
            [master_clean],
        ]
        try:
            asyncio.run(service.link_duplicate_complaint(child_id, master_id, pwd_official))
            assert False, "Expected 403"
        except HTTPException as exc:
            assert exc.status_code == 403
            assert "designated safety officer" in exc.detail.lower()

    print("[PASS] Test 38: All role boundaries and safety restrictions verified intact")


# ==============================================================================
# MAIN RUNNER
# ==============================================================================

def run_all_tests():
    print("=" * 80)
    print("M4-04 COMPREHENSIVE INTEGRATION & SECURITY TEST SUITE (38 TESTS)")
    print("=" * 80)

    tests = [
        test_1_successful_ai_creation,
        test_2_ai_summary_mapping,
        test_3_ai_severity_mapping,
        test_4_ai_category_mapping,
        test_5_department_uuid_resolved_from_ai_category,
        test_6_unassigned_fallback_when_department_not_found,
        test_7_deterministic_fallback_when_gemini_raises,
        test_8_citizen_identity_cannot_be_overwritten,
        test_9_safety_union_rule_citizen_safety_preserved,
        test_10_safety_union_rule_ai_safety_upgraded,
        test_11_initial_priority_calculation,
        test_12_priority_recalculated_on_duplicate_linking,
        test_13_explicit_official_priority_override_preserved,
        test_14_advisory_duplicates_returned_for_official,
        test_15_ordinary_official_filtered_from_safety_duplicates,
        test_16_safety_officer_can_see_safety_duplicates,
        test_17_citizen_blocked_from_duplicates,
        test_18_advisory_duplicate_detection_strictly_read_only,
        test_19_authorized_official_duplicate_linking,
        test_20_cross_department_duplicate_linking_rejected,
        test_21_self_linking_rejected,
        test_22_child_already_linked_rejected,
        test_23_master_cannot_be_child_multi_tier_rejected,
        test_24_master_report_count_and_priority_recalculated,
        test_25_timeline_updates_logged_for_both_child_and_master,
        test_26_duplicate_candidate_ids_using_complaint_id,
        test_27_backward_compatibility_with_id_key,
        test_28_ordinary_official_safety_filtering_member3_shape,
        test_29_master_update_unsuccessful_triggers_child_rollback,
        test_30_master_update_transport_exception_triggers_child_rollback,
        test_31_child_history_failure_triggers_compensating_rollback,
        test_32_master_history_failure_triggers_compensating_rollback,
        test_33_rollback_restores_previous_master_count_and_priority,
        test_34_only_current_operation_history_is_removed,
        test_35_rollback_failure_logged_and_not_falsely_reported,
        test_36_concurrent_duplicate_links_preserve_both_increments,
        test_37_failed_operation_releases_lock_safely,
        test_38_existing_authorization_and_lifecycle_tests,
    ]

    passed = 0
    failed = 0
    for idx, t in enumerate(tests, 1):
        try:
            t()
            passed += 1
        except Exception as exc:
            print(f"[FAIL] Test {idx} ({t.__name__}) failed: {exc}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 80)
    print(f"RESULTS: {passed}/{len(tests)} passed, {failed} failed.")
    print("=" * 80)
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
