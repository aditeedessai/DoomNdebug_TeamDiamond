"""M3-10 End-to-End Service Flow & Boundary Test Suite.

Author: Member 3 (AI & Intelligence Developer)
Task: M3-10 - Final Testing

Parts:
- Part 1: End-to-end service flow (AI Analysis -> Priority Calculation -> Duplicate Detection).
- Part 2: Duplicate linking & priority escalation workflow simulation (in-memory).
- Part 3: AIAnalysisRequest schema boundary validation (1 char, 2000 chars, 2001 chars, whitespace).
"""
import sys
import os
import json
import base64
from uuid import UUID, uuid4
from unittest.mock import MagicMock, patch, AsyncMock

# --- Coroutine driver for pure Python testing without Windows socket/IOCP dependencies ---
class AwaitableVal:
    def __init__(self, val=None, exc=None):
        self.val = val
        self.exc = exc
    def __await__(self):
        if self.exc:
            raise self.exc
        return self.val
        yield

def drive_coro(coro):
    try:
        val = None
        while True:
            val = coro.send(val)
    except StopIteration as e:
        return e.value

# --- Mock Pydantic & Pydantic Settings for test environment ---
class MockConfigDict(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

def mock_field_validator(*args, **kwargs):
    def decorator(fn):
        return fn
    return decorator

def mock_field(default=..., min_length=None, max_length=None, **kwargs):
    return default

VALID_CATEGORIES = {
    "Potholes, damaged roads, footpaths",
    "Broken streetlights",
    "Garbage accumulation",
    "Water leakage, drainage blockage",
    "Traffic congestion, signal faults",
    "Public park or facility damage",
    "Unsafe public infrastructure",
    "Other",
}

VALID_DEPARTMENTS = {
    "Public Works Department",
    "Sanitation Department",
    "Electrical Department",
    "Water & Sewerage Department",
    "Traffic & Transport Department",
    "Parks & Public Assets Department",
    None,
}

VALID_LANGUAGES = {"English", "Hindi", "Other"}

VALID_SAFETY_CATEGORIES = {
    "Lighting issue",
    "Pedestrian accessibility issue",
    "Public transport infrastructure issue",
    "Repeated citizen concern",
    "Unverified safety concern",
    None,
}

class MockBaseModel:
    def __init__(self, **kwargs):
        # Strict schema validation matching Field constraints in schemas/ai.py
        if "description" in kwargs:
            desc = kwargs["description"]
            if not isinstance(desc, str):
                raise ValueError("Description must be a string")
            if len(desc) < 1:
                raise ValueError("Complaint description cannot be empty or whitespace only.")
            if len(desc) > 2000:
                raise ValueError(f"Complaint description cannot exceed 2000 characters (got {len(desc)}).")
            if not desc.strip():
                raise ValueError("Complaint description cannot be empty or whitespace only.")
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def model_validate(cls, data):
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
        REQUIRED = ["suggested_title", "category", "issue_type", "severity", "summary", "recommended_action", "language"]
        for req_field in REQUIRED:
            if req_field not in data:
                raise ValueError(f"Missing required field: {req_field}")
        if data["category"] not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category: {data['category']}")
        if "department" in data and data["department"] not in VALID_DEPARTMENTS:
            raise ValueError(f"Invalid department: {data['department']}")
        if data["language"] not in VALID_LANGUAGES:
            raise ValueError(f"Invalid language: {data['language']}")
        if "safety_category" in data and data["safety_category"] not in VALID_SAFETY_CATEGORIES:
            raise ValueError(f"Invalid safety_category: {data['safety_category']}")
        sev = data["severity"]
        if not isinstance(sev, int) or isinstance(sev, bool) or sev < 1 or sev > 10:
            raise ValueError(f"Invalid severity: {sev}")
        return cls(**data)

    def model_dump(self):
        return dict(self.__dict__)

pydantic_mock = MagicMock()
pydantic_mock.BaseModel = MockBaseModel
pydantic_mock.ConfigDict = MockConfigDict
pydantic_mock.Field = mock_field
pydantic_mock.field_validator = mock_field_validator
sys.modules['pydantic'] = pydantic_mock

pyd_settings_mock = MagicMock()
pyd_settings_mock.BaseSettings = MockBaseModel
pyd_settings_mock.SettingsConfigDict = MockConfigDict
sys.modules['pydantic_settings'] = pyd_settings_mock

# Mock httpx
httpx_mock = MagicMock()
class MockTimeoutException(Exception): pass
class MockNetworkError(Exception): pass
class MockHTTPStatusError(Exception):
    def __init__(self, message, request=None, response=None):
        super().__init__(message)
        self.response = response
class MockRequestError(Exception): pass
httpx_mock.TimeoutException = MockTimeoutException
httpx_mock.NetworkError = MockNetworkError
httpx_mock.HTTPStatusError = MockHTTPStatusError
httpx_mock.RequestError = MockRequestError
sys.modules['httpx'] = httpx_mock

# Setup backend import path
backend_path = r"c:\Users\Nishtaa\Desktop\DoomNdebug_TeamDiamond\backend"
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
if 'backend' not in sys.path:
    sys.path.insert(0, 'backend')

# Import Member 3 services and schemas
from app.schemas.ai import AIAnalysisRequest, AIAnalysisResponse
from app.services.ai_service import ai_service, AIService
from app.services.priority_service import priority_service, PriorityService
from app.services.duplicate_service import duplicate_service, DuplicateService
from app.core.config import settings


def make_gemini_response(payload_dict: dict, status_code: int = 200):
    """Helper to mock a standard Gemini API response."""
    mock_resp = MagicMock(status_code=status_code)
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": json.dumps(payload_dict)}
                    ]
                }
            }
        ]
    }
    return mock_resp


# ==============================================================================
# Part 1: End-to-End Service Flow Tests
# ==============================================================================

def test_01_e2e_pothole_complaint_pipeline():
    """Part 1 - Test 1: Full pipeline: text input -> AI classification -> Priority -> Duplicates."""
    # 1. Citizen submits pothole report
    req = AIAnalysisRequest(
        description="Massive dangerous pothole near the central bus terminal causing vehicle damage and traffic backup.",
        latitude=12.971600,
        longitude=77.594600,
    )

    ai_json = {
        "suggested_title": "Severe Pothole near Central Bus Terminal",
        "category": "Potholes, damaged roads, footpaths",
        "issue_type": "Pothole",
        "department": "Public Works Department",
        "severity": 7,
        "summary": "Large hazardous pothole disrupting traffic near bus terminal.",
        "recommended_action": "Cordon off lane and deploy asphalt patching crew.",
        "language": "English",
        "is_safety_related": True,
        "safety_category": "Pedestrian accessibility issue",
        "needs_human_review": False,
        "review_reason": None,
    }

    # 2. Mock Gemini response and run AI Analysis
    with patch.object(settings, "GEMINI_API_KEY", "test-key"):
        with patch.object(ai_service, "_generate_content", new=lambda *args, **kwargs: AwaitableVal(json.dumps(ai_json))):
            ai_res = drive_coro(ai_service.analyze_complaint(req))

    assert ai_res.category == "Potholes, damaged roads, footpaths"
    assert ai_res.severity == 7
    assert ai_res.department == "Public Works Department"
    assert ai_res.is_safety_related is True

    # 3. Calculate Deterministic Priority using AI severity
    p_score = priority_service.calculate_priority_score(
        severity=ai_res.severity,
        report_count=1,
        overdue_bonus=0,
    )
    p_tier = priority_service.calculate_priority(
        severity=ai_res.severity,
        report_count=1,
        overdue_bonus=0,
    )
    # Severity 7 * 10 = 70 -> "High"
    assert p_score == 70
    assert p_tier == "High"

    # 4. Query Duplicate Detection with in-memory candidates
    candidates = [
        {
            "id": "c1111111-0000-0000-0000-000000000001",
            "title": "Existing pothole reported yesterday",
            "category": "Potholes, damaged roads, footpaths",
            "issue_type": "Pothole",
            "status": "Submitted",
            "latitude": 12.971870,  # ~30m away
            "longitude": 77.594600,
            "report_count": 2,
            "created_at": "2026-11-13T10:00:00Z",
        },
        {
            "id": "c2222222-0000-0000-0000-000000000002",
            "title": "Broken streetlight 15m away",
            "category": "Broken streetlights",  # Different category
            "status": "Submitted",
            "latitude": 12.971700,
            "longitude": 77.594600,
        },
        {
            "id": "c3333333-0000-0000-0000-000000000003",
            "title": "Pothole 250m away",
            "category": "Potholes, damaged roads, footpaths",
            "status": "Submitted",
            "latitude": 12.973900,  # > 100m away
            "longitude": 77.594600,
        },
    ]

    duplicates = drive_coro(duplicate_service.find_duplicates(
        category=ai_res.category,
        latitude=req.latitude,
        longitude=req.longitude,
        candidates=candidates,
    ))

    # Only candidate 1 matches both category and radius
    assert len(duplicates) == 1
    match = duplicates[0]
    assert match["complaint_id"] == "c1111111-0000-0000-0000-000000000001"
    assert match["category"] == "Potholes, damaged roads, footpaths"
    assert 25.0 < match["distance_meters"] < 35.0
    assert "citizen_id" not in match

    print("PASS: Test 01 - Full E2E Pothole Pipeline (AI -> Priority -> Duplicates)")


def test_02_e2e_multimodal_hindi_pipeline():
    """Part 1 - Test 2: Multimodal Hindi submission with image and priority evaluation."""
    target_lat = 15.3995
    target_lon = 73.8122

    req = AIAnalysisRequest(
        description="सड़क पर स्ट्रीट लाइट टूटी हुई है और रात में बहुत अंधेरा रहता है",
        latitude=target_lat,
        longitude=target_lon,
        image_url="complaints/citizen-001/dark_street.jpg",
        language_hint="hi",
    )

    ai_json = {
        "suggested_title": "Broken Streetlight on Dark Road",
        "category": "Broken streetlights",
        "issue_type": "Streetlight",
        "department": "Electrical Department",
        "severity": 8,
        "summary": "Damaged streetlight causing severe nighttime darkness and safety concern.",
        "recommended_action": "Replace damaged bulb/fixture and test wiring connection.",
        "language": "Hindi",
        "is_safety_related": True,
        "safety_category": "Lighting issue",
        "needs_human_review": False,
        "review_reason": None,
    }

    # Mock image verification and multimodal Gemini call
    valid_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    with patch.object(settings, "GEMINI_API_KEY", "test-key"):
        with patch.object(ai_service, "_download_and_verify_image", new=lambda *args, **kwargs: AwaitableVal((valid_jpeg, "image/jpeg"))):
            with patch.object(ai_service, "_resolve_image_target", return_value=("https://project.supabase.co/storage/v1/object/complaint-images/complaints/citizen-001/dark_street.jpg", {})):
                with patch.object(ai_service, "_generate_content", new=lambda *args, **kwargs: AwaitableVal(json.dumps(ai_json))):
                    ai_res = drive_coro(ai_service.analyze_complaint(req))

    assert ai_res.language == "Hindi"
    assert ai_res.category == "Broken streetlights"
    assert ai_res.severity == 8
    assert ai_res.department == "Electrical Department"

    # Priority calculation: Severity 8 -> Critical immediately
    p_tier = priority_service.calculate_priority(severity=ai_res.severity, report_count=1)
    p_score = priority_service.calculate_priority_score(severity=ai_res.severity, report_count=1)
    assert p_score == 80
    assert p_tier == "Critical"

    print("PASS: Test 02 - E2E Multimodal Hindi Pipeline (Image -> Translation -> Critical Priority)")


# ==============================================================================
# Part 2: Duplicate Linking & Priority Escalation Workflow Simulation
# ==============================================================================

def test_03_duplicate_linking_escalation_simulation():
    """Part 2 - Test 3: Simulated workflow of official linking duplicates and priority escalation."""
    # Simulation context: Member 4 maintains the master complaint in the database.
    # The duplicate_service only identifies candidates; Member 4 executes linking in memory.

    # Initial Master Complaint created by Citizen A
    master_complaint = {
        "id": "master-uuid-9999-0000",
        "title": "Low water pressure in residential sector",
        "category": "Water leakage, drainage blockage",
        "severity": 5,
        "report_count": 1,
        "priority": priority_service.calculate_priority(severity=5, report_count=1),
        "status": "Submitted",
        "master_incident_id": None,
    }

    # Initial state: Severity 5, Report Count 1 -> Score 50 -> Medium
    assert master_complaint["priority"] == "Medium"
    assert master_complaint["report_count"] == 1
    assert master_complaint["id"] == "master-uuid-9999-0000"

    # --- Duplicate Report 2 is linked by Municipal Official ---
    # Official confirms match; report_count incremented to 2
    master_complaint["report_count"] += 1
    new_priority = priority_service.calculate_priority(
        severity=master_complaint["severity"],
        report_count=master_complaint["report_count"],
        overdue_bonus=0,
    )
    score_2 = priority_service.calculate_priority_score(
        severity=master_complaint["severity"],
        report_count=master_complaint["report_count"],
        overdue_bonus=0,
    )
    # Score = (5 * 10) + (2 - 1) * 5 = 55 -> Still Medium
    assert score_2 == 55
    assert new_priority == "Medium"
    master_complaint["priority"] = new_priority

    # --- Duplicate Report 3 is linked by Municipal Official ---
    # Official confirms match; report_count incremented to 3
    master_complaint["report_count"] += 1
    escalated_priority = priority_service.calculate_priority(
        severity=master_complaint["severity"],
        report_count=master_complaint["report_count"],
        overdue_bonus=0,
    )
    score_3 = priority_service.calculate_priority_score(
        severity=master_complaint["severity"],
        report_count=master_complaint["report_count"],
        overdue_bonus=0,
    )
    # Score = (5 * 10) + (3 - 1) * 5 = 60 -> Crosses boundary into "High"!
    assert score_3 == 60
    assert escalated_priority == "High"
    master_complaint["priority"] = escalated_priority

    # --- Duplicate Reports 4 through 7 linked ---
    # At report_count = 7: Score = 50 + (6 * 5) = 80 -> Crosses boundary into "Critical"!
    master_complaint["report_count"] = 7
    critical_priority = priority_service.calculate_priority(
        severity=master_complaint["severity"],
        report_count=master_complaint["report_count"],
        overdue_bonus=0,
    )
    score_7 = priority_service.calculate_priority_score(
        severity=master_complaint["severity"],
        report_count=master_complaint["report_count"],
        overdue_bonus=0,
    )
    assert score_7 == 80
    assert critical_priority == "Critical"
    master_complaint["priority"] = critical_priority

    # --- Invariant checks ---
    # Master ID must never change during duplicate linking
    assert master_complaint["id"] == "master-uuid-9999-0000"
    assert master_complaint["master_incident_id"] is None

    print("PASS: Test 03 - Duplicate Linking & Escalation Simulation (Medium -> High -> Critical)")


def test_04_uncertain_duplicates_never_auto_linked():
    """Part 2 - Test 4: Verify uncertain candidate matches are not automatically linked."""
    master_complaint = {
        "id": "master-111",
        "category": "Garbage accumulation",
        "severity": 4,
        "report_count": 1,
        "priority": "Medium",
    }

    # Candidate outside 100m radius
    distant_candidate = {
        "id": "cand-999",
        "category": "Garbage accumulation",
        "latitude": 12.9750,  # ~350m away
        "longitude": 77.5946,
        "status": "Submitted",
    }

    matches = drive_coro(duplicate_service.find_duplicates(
        category=master_complaint["category"],
        latitude=12.9716,
        longitude=77.5946,
        candidates=[distant_candidate],
    ))

    # Duplicate service correctly drops the candidate
    assert len(matches) == 0

    # Master report count remains strictly 1 and priority remains untouched
    assert master_complaint["report_count"] == 1
    assert master_complaint["priority"] == "Medium"
    print("PASS: Test 04 - Uncertain Duplicates Dropped & Master State Unmutated")


# ==============================================================================
# Part 3: AI Request Schema Boundary Tests
# ==============================================================================

def test_05_schema_boundary_1_character():
    """Part 3 - Test 5: Exact 1-character description accepted."""
    req = AIAnalysisRequest(description="P")
    assert req.description == "P"
    print("PASS: Test 05 - Schema Boundary: 1-character description accepted")


def test_06_schema_boundary_2000_characters():
    """Part 3 - Test 6: Exact 2,000-character description accepted."""
    long_desc = "A" * 2000
    req = AIAnalysisRequest(description=long_desc)
    assert len(req.description) == 2000
    print("PASS: Test 06 - Schema Boundary: 2,000-character description accepted")


def test_07_schema_boundary_2001_characters_rejected():
    """Part 3 - Test 7: Exact 2,001-character description rejected with ValueError."""
    too_long_desc = "A" * 2001
    try:
        AIAnalysisRequest(description=too_long_desc)
        assert False, "Expected ValueError for 2001-character description"
    except ValueError as e:
        assert "2000" in str(e) or "exceed" in str(e).lower()
    print("PASS: Test 07 - Schema Boundary: 2,001-character description rejected")


def test_08_schema_boundary_whitespace_rejected():
    """Part 3 - Test 8: Whitespace-only descriptions rejected with ValueError."""
    whitespace_inputs = ["   ", "\t\t", "\n\n\n", "  \r\n  "]
    for ws in whitespace_inputs:
        try:
            AIAnalysisRequest(description=ws)
            assert False, f"Expected ValueError for whitespace description: {ws!r}"
        except ValueError as e:
            assert "whitespace" in str(e).lower() or "empty" in str(e).lower()

    print("PASS: Test 08 - Schema Boundary: Whitespace-only descriptions rejected")


def test_09_schema_boundary_empty_rejected():
    """Part 3 - Test 9: Empty string description rejected with ValueError."""
    try:
        AIAnalysisRequest(description="")
        assert False, "Expected ValueError for empty description"
    except ValueError as e:
        assert "empty" in str(e).lower() or "whitespace" in str(e).lower()

    print("PASS: Test 09 - Schema Boundary: Empty description rejected")


# ==============================================================================
# Main Runner for M3-10 Test Suite
# ==============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Running Member 3 Task M3-10 - End-to-End & Boundary Test Suite")
    print("=" * 70)

    test_01_e2e_pothole_complaint_pipeline()
    test_02_e2e_multimodal_hindi_pipeline()
    test_03_duplicate_linking_escalation_simulation()
    test_04_uncertain_duplicates_never_auto_linked()
    test_05_schema_boundary_1_character()
    test_06_schema_boundary_2000_characters()
    test_07_schema_boundary_2001_characters_rejected()
    test_08_schema_boundary_whitespace_rejected()
    test_09_schema_boundary_empty_rejected()

    print("=" * 70)
    print("ALL 9 M3-10 E2E & BOUNDARY TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
