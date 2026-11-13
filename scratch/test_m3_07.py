"""M3-07 Duplicate Matching Test Suite (14 Scenarios + Supabase End-to-End).

Tests:
1. Same category, within 100m -> Detected as duplicate
2. Same category, beyond 100m -> Filtered out by distance
3. Different category, identical coordinates -> Filtered out (category mismatch)
4. Missing target coordinates (None) -> Gracefully returns []
5. Invalid target and candidate coordinates (NaN, inf, out of range, bool, str) -> Rejected
6. Self-matching prevention (exclude_complaint_id matching candidate id, str & UUID) -> Excluded
7. Multiple matches sorted ascending by distance_meters -> Correct order
8. Resolved and Rejected filtering when active_only=True -> Excluded
9. active_only=False behavior -> Resolved & Rejected included
10. Invalid radius values (0, negative, NaN, inf, bool, str) -> Gracefully returns []
11. Supabase query failure (None, non-list, exception) -> Gracefully returns []
12. No database writes -> rest_query only invoked with method="GET"
13. No personal information in returned dicts (Zero PII verification)
14. Haversine edge cases (identical coords, equator, poles, antipodal clamp, booleans)
Plus: Supabase candidate query end-to-end integration with params verification.
"""
import sys
import os
import math
from uuid import UUID, uuid4
from unittest.mock import MagicMock, AsyncMock, patch

# --- Coroutine driver for pure Python testing without Windows socket/IOCP dependencies ---
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

def mock_field(default=..., **kwargs):
    return default

class MockBaseModel:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def model_validate(cls, data):
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
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

# Set backend path
backend_path = r"c:\Users\Nishtaa\Desktop\DoomNdebug_TeamDiamond\backend"
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
if 'backend' not in sys.path:
    sys.path.insert(0, 'backend')

# Import duplicate service after mock and path setup
from app.services.duplicate_service import (
    DuplicateService,
    duplicate_service,
    _validate_coordinate,
    CANONICAL_CATEGORIES,
    EARTH_RADIUS_METRES,
)


def test_01_same_category_within_100m():
    """Test 1: Same category within 100m is detected as duplicate."""
    target_lat = 12.971600
    target_lon = 77.594600
    cand_lat = 12.971870  # ~30m north
    cand_lon = 77.594600

    candidates = [
        {
            "id": "c1111111-1111-1111-1111-111111111111",
            "title": "Deep pothole near junction",
            "category": "Potholes, damaged roads, footpaths",
            "issue_type": "Pothole",
            "status": "Submitted",
            "latitude": cand_lat,
            "longitude": cand_lon,
            "report_count": 2,
            "created_at": "2026-11-14T00:00:00Z",
        }
    ]

    res = drive_coro(duplicate_service.find_duplicates(
        category="Potholes, damaged roads, footpaths",
        latitude=target_lat,
        longitude=target_lon,
        candidates=candidates,
    ))

    assert len(res) == 1, f"Expected 1 duplicate, got {len(res)}"
    item = res[0]
    assert item["complaint_id"] == "c1111111-1111-1111-1111-111111111111"
    assert item["category"] == "Potholes, damaged roads, footpaths"
    assert 25.0 < item["distance_meters"] < 35.0, f"Distance unexpected: {item['distance_meters']}"
    assert item["report_count"] == 2
    print("PASS: Test 01 - Same category within 100m detected.")


def test_02_same_category_beyond_100m():
    """Test 2: Same category beyond 100m is excluded."""
    target_lat = 12.971600
    target_lon = 77.594600
    cand_lat = 12.973400  # ~200m north
    cand_lon = 77.594600

    candidates = [
        {
            "id": "c2222222-2222-2222-2222-222222222222",
            "title": "Pothole 200m away",
            "category": "Potholes, damaged roads, footpaths",
            "issue_type": "Pothole",
            "status": "Submitted",
            "latitude": cand_lat,
            "longitude": cand_lon,
        }
    ]

    res = drive_coro(duplicate_service.find_duplicates(
        category="Potholes, damaged roads, footpaths",
        latitude=target_lat,
        longitude=target_lon,
        candidates=candidates,
    ))

    assert len(res) == 0, f"Expected 0 duplicates for candidate at 200m, got {len(res)}"
    print("PASS: Test 02 - Same category beyond 100m excluded.")


def test_03_different_category_identical_coords():
    """Test 3: Different category with identical coordinates is excluded."""
    target_lat = 12.971600
    target_lon = 77.594600

    candidates = [
        {
            "id": "c3333333-3333-3333-3333-333333333333",
            "title": "Broken streetlight right here",
            "category": "Broken streetlights",
            "issue_type": "Streetlight",
            "status": "Submitted",
            "latitude": target_lat,
            "longitude": target_lon,
        }
    ]

    res = drive_coro(duplicate_service.find_duplicates(
        category="Potholes, damaged roads, footpaths",
        latitude=target_lat,
        longitude=target_lon,
        candidates=candidates,
    ))

    assert len(res) == 0, f"Expected 0 duplicates due to category mismatch, got {len(res)}"
    print("PASS: Test 03 - Different category at identical coords excluded.")


def test_04_missing_target_coords():
    """Test 4: Missing target coordinates gracefully return []."""
    candidates = [
        {
            "id": "c4444444-4444-4444-4444-444444444444",
            "category": "Broken streetlights",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "status": "Submitted",
        }
    ]

    # Target lat None
    res1 = drive_coro(duplicate_service.find_duplicates(
        category="Broken streetlights",
        latitude=None,
        longitude=77.5946,
        candidates=candidates,
    ))
    assert res1 == [], f"Expected [], got {res1}"

    # Target lon None
    res2 = drive_coro(duplicate_service.find_duplicates(
        category="Broken streetlights",
        latitude=12.9716,
        longitude=None,
        candidates=candidates,
    ))
    assert res2 == [], f"Expected [], got {res2}"

    # Both None
    res3 = drive_coro(duplicate_service.find_duplicates(
        category="Broken streetlights",
        latitude=None,
        longitude=None,
        candidates=candidates,
    ))
    assert res3 == [], f"Expected [], got {res3}"
    print("PASS: Test 04 - Missing target coordinates handled safely.")


def test_05_invalid_target_and_candidate_coords():
    """Test 5: Invalid coordinates (NaN, inf, out of range, bool, str)."""
    # 5a: Target lat > 90
    res_lat_high = drive_coro(duplicate_service.find_duplicates(
        category="Broken streetlights",
        latitude=91.0,
        longitude=77.5946,
        candidates=[],
    ))
    assert res_lat_high == []

    # 5b: Target lon < -180
    res_lon_low = drive_coro(duplicate_service.find_duplicates(
        category="Broken streetlights",
        latitude=12.97,
        longitude=-181.0,
        candidates=[],
    ))
    assert res_lon_low == []

    # 5c: Target lat NaN / inf
    res_nan = drive_coro(duplicate_service.find_duplicates(
        category="Broken streetlights",
        latitude=float("nan"),
        longitude=77.5946,
        candidates=[],
    ))
    assert res_nan == []

    res_inf = drive_coro(duplicate_service.find_duplicates(
        category="Broken streetlights",
        latitude=12.97,
        longitude=float("inf"),
        candidates=[],
    ))
    assert res_inf == []

    # 5d: Target lat bool True (should not be treated as 1.0)
    res_bool = drive_coro(duplicate_service.find_duplicates(
        category="Broken streetlights",
        latitude=True,
        longitude=77.5946,
        candidates=[],
    ))
    assert res_bool == []

    # 5e: Candidate with invalid coordinates should be skipped, not crash
    candidates = [
        {
            "id": "cand-invalid-nan",
            "category": "Broken streetlights",
            "status": "Submitted",
            "latitude": float("nan"),
            "longitude": 77.5946,
        },
        {
            "id": "cand-invalid-out-of-range",
            "category": "Broken streetlights",
            "status": "Submitted",
            "latitude": 99.0,
            "longitude": 77.5946,
        },
        {
            "id": "cand-invalid-str",
            "category": "Broken streetlights",
            "status": "Submitted",
            "latitude": "not-a-number",
            "longitude": 77.5946,
        },
        {
            "id": "cand-invalid-bool",
            "category": "Broken streetlights",
            "status": "Submitted",
            "latitude": False,
            "longitude": 77.5946,
        },
        {
            "id": "cand-valid",
            "category": "Broken streetlights",
            "status": "Submitted",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    ]

    res_cands = drive_coro(duplicate_service.find_duplicates(
        category="Broken streetlights",
        latitude=12.9716,
        longitude=77.5946,
        candidates=candidates,
    ))
    assert len(res_cands) == 1
    assert res_cands[0]["complaint_id"] == "cand-valid"
    print("PASS: Test 05 - Invalid target and candidate coordinates rejected.")


def test_06_self_matching_prevention():
    """Test 6: Self-matching prevention with UUID and string formats."""
    target_id_str = "a1b2c3d4-0000-0000-0000-000000000001"
    target_id_uuid = UUID(target_id_str)

    candidates = [
        {
            "id": target_id_str.upper(),  # Test case-insensitivity
            "category": "Garbage accumulation",
            "status": "Submitted",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
        {
            "id": "other-id-0002",
            "category": "Garbage accumulation",
            "status": "Submitted",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    ]

    # Exclude using string
    res_str = drive_coro(duplicate_service.find_duplicates(
        category="Garbage accumulation",
        latitude=12.9716,
        longitude=77.5946,
        exclude_complaint_id=target_id_str,
        candidates=candidates,
    ))
    assert len(res_str) == 1
    assert res_str[0]["complaint_id"] == "other-id-0002"

    # Exclude using UUID object
    res_uuid = drive_coro(duplicate_service.find_duplicates(
        category="Garbage accumulation",
        latitude=12.9716,
        longitude=77.5946,
        exclude_complaint_id=target_id_uuid,
        candidates=candidates,
    ))
    assert len(res_uuid) == 1
    assert res_uuid[0]["complaint_id"] == "other-id-0002"
    print("PASS: Test 06 - Self-matching prevention verified for str and UUID.")


def test_07_multiple_matches_sorted_by_distance():
    """Test 7: Multiple matches sorted ascending by distance_meters."""
    target_lat = 12.971600
    target_lon = 77.594600

    candidates = [
        {
            "id": "cand-80m",
            "category": "Water leakage, drainage blockage",
            "status": "Submitted",
            "latitude": 12.972320,
            "longitude": target_lon,
        },
        {
            "id": "cand-15m",
            "category": "Water leakage, drainage blockage",
            "status": "Assigned",
            "latitude": 12.971735,
            "longitude": target_lon,
        },
        {
            "id": "cand-50m",
            "category": "Water leakage, drainage blockage",
            "status": "In Progress",
            "latitude": 12.972050,
            "longitude": target_lon,
        },
    ]

    res = drive_coro(duplicate_service.find_duplicates(
        category="Water leakage, drainage blockage",
        latitude=target_lat,
        longitude=target_lon,
        candidates=candidates,
    ))

    assert len(res) == 3, f"Expected 3 matches, got {len(res)}"
    assert res[0]["complaint_id"] == "cand-15m"
    assert res[1]["complaint_id"] == "cand-50m"
    assert res[2]["complaint_id"] == "cand-80m"
    assert res[0]["distance_meters"] <= res[1]["distance_meters"] <= res[2]["distance_meters"]
    print("PASS: Test 07 - Multiple matches properly sorted ascending by distance.")


def test_08_resolved_and_rejected_filtering_active_only():
    """Test 8: Resolved and Rejected candidates excluded when active_only=True."""
    target_lat = 12.971600
    target_lon = 77.594600

    candidates = [
        {
            "id": "cand-active-sub",
            "category": "Traffic congestion, signal faults",
            "status": "Submitted",
            "latitude": target_lat,
            "longitude": target_lon,
        },
        {
            "id": "cand-active-review",
            "category": "Traffic congestion, signal faults",
            "status": "Under Review",
            "latitude": target_lat,
            "longitude": target_lon,
        },
        {
            "id": "cand-resolved",
            "category": "Traffic congestion, signal faults",
            "status": "Resolved",
            "latitude": target_lat,
            "longitude": target_lon,
        },
        {
            "id": "cand-rejected",
            "category": "Traffic congestion, signal faults",
            "status": "Rejected",
            "latitude": target_lat,
            "longitude": target_lon,
        },
    ]

    res = drive_coro(duplicate_service.find_duplicates(
        category="Traffic congestion, signal faults",
        latitude=target_lat,
        longitude=target_lon,
        active_only=True,
        candidates=candidates,
    ))

    ids = [m["complaint_id"] for m in res]
    assert "cand-resolved" not in ids, "Resolved complaint should be excluded when active_only=True"
    assert "cand-rejected" not in ids, "Rejected complaint should be excluded when active_only=True"
    assert "cand-active-sub" in ids
    assert "cand-active-review" in ids
    assert len(res) == 2
    print("PASS: Test 08 - Resolved and Rejected excluded when active_only=True.")


def test_09_active_only_false_includes_resolved():
    """Test 9: active_only=False includes Resolved and Rejected complaints."""
    target_lat = 12.971600
    target_lon = 77.594600

    candidates = [
        {
            "id": "cand-active-sub",
            "category": "Traffic congestion, signal faults",
            "status": "Submitted",
            "latitude": target_lat,
            "longitude": target_lon,
        },
        {
            "id": "cand-resolved",
            "category": "Traffic congestion, signal faults",
            "status": "Resolved",
            "latitude": target_lat,
            "longitude": target_lon,
        },
        {
            "id": "cand-rejected",
            "category": "Traffic congestion, signal faults",
            "status": "Rejected",
            "latitude": target_lat,
            "longitude": target_lon,
        },
    ]

    res = drive_coro(duplicate_service.find_duplicates(
        category="Traffic congestion, signal faults",
        latitude=target_lat,
        longitude=target_lon,
        active_only=False,
        candidates=candidates,
    ))

    ids = [m["complaint_id"] for m in res]
    assert "cand-resolved" in ids
    assert "cand-rejected" in ids
    assert "cand-active-sub" in ids
    assert len(res) == 3
    print("PASS: Test 09 - active_only=False correctly includes resolved and rejected.")


def test_10_invalid_radius_values():
    """Test 10: Invalid radius values (zero, negative, NaN, inf, bool, str) return []."""
    target_lat = 12.971600
    target_lon = 77.594600
    candidates = [
        {
            "id": "cand-1",
            "category": "Public park or facility damage",
            "status": "Submitted",
            "latitude": target_lat,
            "longitude": target_lon,
        }
    ]

    invalid_radii = [0, 0.0, -10.0, float("nan"), float("inf"), float("-inf"), True, False, "100m", None]

    for r in invalid_radii:
        res = drive_coro(duplicate_service.find_duplicates(
            category="Public park or facility damage",
            latitude=target_lat,
            longitude=target_lon,
            radius_metres=r,
            candidates=candidates,
        ))
        assert res == [], f"Expected [] for radius {r}, got {res}"

    print("PASS: Test 10 - Invalid radius values safely return [].")


def test_11_supabase_query_failure():
    """Test 11: Supabase query failure (None, non-list, exception) returns []."""
    from app.database.supabase import supabase_service

    target_lat = 12.971600
    target_lon = 77.594600

    # 11a: rest_query returns None
    with patch.object(supabase_service, "rest_query", new_callable=AsyncMock) as mock_rq:
        mock_rq.return_value = None
        res_none = drive_coro(duplicate_service.find_duplicates(
            category="Unsafe public infrastructure",
            latitude=target_lat,
            longitude=target_lon,
            candidates=None,
        ))
        assert res_none == [], f"Expected [], got {res_none}"

    # 11b: rest_query returns a dict error
    with patch.object(supabase_service, "rest_query", new_callable=AsyncMock) as mock_rq:
        mock_rq.return_value = {"error": "Service unavailable"}
        res_dict = drive_coro(duplicate_service.find_duplicates(
            category="Unsafe public infrastructure",
            latitude=target_lat,
            longitude=target_lon,
            candidates=None,
        ))
        assert res_dict == [], f"Expected [], got {res_dict}"

    # 11c: rest_query raises an exception
    with patch.object(supabase_service, "rest_query", new_callable=AsyncMock) as mock_rq:
        mock_rq.side_effect = RuntimeError("Connection timeout")
        res_exc = drive_coro(duplicate_service.find_duplicates(
            category="Unsafe public infrastructure",
            latitude=target_lat,
            longitude=target_lon,
            candidates=None,
        ))
        assert res_exc == [], f"Expected [], got {res_exc}"

    print("PASS: Test 11 - Supabase query failures handled gracefully.")


def test_12_no_database_writes():
    """Test 12: Ensure DuplicateService NEVER performs database writes (POST, PUT, PATCH, DELETE)."""
    from app.database.supabase import supabase_service

    target_lat = 12.971600
    target_lon = 77.594600

    with patch.object(supabase_service, "rest_query", new_callable=AsyncMock) as mock_rq:
        mock_rq.return_value = []
        res = drive_coro(duplicate_service.find_duplicates(
            category="Potholes, damaged roads, footpaths",
            latitude=target_lat,
            longitude=target_lon,
            candidates=None,
        ))
        assert res == []

        # Verify rest_query was called with GET only
        assert mock_rq.call_count == 1
        args, kwargs = mock_rq.call_args
        assert args[0] == "complaints"
        assert kwargs.get("method") == "GET"

    print("PASS: Test 12 - Read-only guarantee confirmed: method='GET' only.")


def test_13_no_personal_information_in_results():
    """Test 13: Zero PII verification - citizen_id, phone, description, etc. are stripped."""
    target_lat = 12.971600
    target_lon = 77.594600

    candidates = [
        {
            "id": "c-pii-test",
            "citizen_id": "99999999-9999-9999-9999-999999999999",
            "phone": "+91 9876543210",
            "description": "Resident Mr. John Doe reported a major garbage overflow outside his home at Flat 402.",
            "title": "Garbage overflow",
            "category": "Garbage accumulation",
            "issue_type": "Garbage overflow",
            "status": "Submitted",
            "latitude": target_lat,
            "longitude": target_lon,
            "report_count": 3,
            "created_at": "2026-11-14T00:00:00Z",
            "user": {"email": "john.doe@example.com", "name": "John Doe"},
            "safety_related": False,
        }
    ]

    res = drive_coro(duplicate_service.find_duplicates(
        category="Garbage accumulation",
        latitude=target_lat,
        longitude=target_lon,
        candidates=candidates,
    ))

    assert len(res) == 1
    match = res[0]

    ALLOWED_KEYS = {
        "complaint_id",
        "title",
        "category",
        "issue_type",
        "status",
        "distance_meters",
        "report_count",
        "created_at",
    }

    assert set(match.keys()) == ALLOWED_KEYS, f"Match keys contain unexpected fields: {set(match.keys()) - ALLOWED_KEYS}"
    assert "citizen_id" not in match
    assert "phone" not in match
    assert "description" not in match
    assert "user" not in match
    assert match["distance_meters"] == 0.0
    assert match["report_count"] == 3
    print("PASS: Test 13 - Zero PII confirmed in returned duplicate summaries.")


def test_14_haversine_edge_cases():
    """Test 14: Haversine edge cases (identical coords, equator, poles, antipodal clamp, booleans)."""
    # 14a: Identical coordinates
    d_zero = duplicate_service.calculate_distance(12.9716, 77.5946, 12.9716, 77.5946)
    assert d_zero == 0.0, f"Expected 0.0, got {d_zero}"

    # 14b: Equator points: (0.0, 0.0) to (0.0, 1.0)
    # Circumference = 2 * pi * 6,371,000 ~ 40,030,173.6 m
    # 1 degree longitude at equator = Circumference / 360 ~ 111,195 m
    d_equator = duplicate_service.calculate_distance(0.0, 0.0, 0.0, 1.0)
    assert 111000.0 < d_equator < 111400.0, f"Expected ~111,195m, got {d_equator}"

    # 14c: North Pole to slightly south (90.0, 0.0) to (89.0, 0.0) -> 1 degree latitude
    d_pole = duplicate_service.calculate_distance(90.0, 0.0, 89.0, 0.0)
    assert 111000.0 < d_pole < 111400.0, f"Expected ~111,195m, got {d_pole}"

    # 14d: Antipodal points (90.0, 0.0) to (-90.0, 0.0) -> Half circumference
    # Should not trigger floating-point domain error due to clamp
    d_antipodal = duplicate_service.calculate_distance(90.0, 0.0, -90.0, 0.0)
    expected_half_circ = math.pi * EARTH_RADIUS_METRES
    assert abs(d_antipodal - expected_half_circ) < 1.0, f"Expected {expected_half_circ}, got {d_antipodal}"

    # 14e: Booleans rejected
    assert duplicate_service.calculate_distance(True, 77.5, 12.9, 77.5) is None
    assert duplicate_service.calculate_distance(12.9, False, 12.9, 77.5) is None

    # 14f: Out of range coordinates
    assert duplicate_service.calculate_distance(90.1, 0.0, 0.0, 0.0) is None
    assert duplicate_service.calculate_distance(0.0, 180.1, 0.0, 0.0) is None

    print("PASS: Test 14 - Haversine edge cases and domain protection verified.")


def test_15_supabase_query_live_params():
    """Test 15: End-to-end Supabase query with candidate processing and parameter verification."""
    from app.database.supabase import supabase_service

    target_lat = 12.971600
    target_lon = 77.594600

    db_rows = [
        {
            "id": "db-cand-001",
            "title": "Severe pothole",
            "category": "Potholes, damaged roads, footpaths",
            "issue_type": "Pothole",
            "status": "Submitted",
            "latitude": 12.971870,  # ~30m
            "longitude": target_lon,
            "report_count": 5,
            "created_at": "2026-11-13T10:00:00Z",
        },
        {
            "id": "db-cand-002",
            "title": "Old pothole 300m away",
            "category": "Potholes, damaged roads, footpaths",
            "issue_type": "Pothole",
            "status": "In Progress",
            "latitude": 12.974500,  # ~320m away
            "longitude": target_lon,
            "report_count": 1,
            "created_at": "2026-11-12T10:00:00Z",
        },
    ]

    with patch.object(supabase_service, "rest_query", new_callable=AsyncMock) as mock_rq:
        mock_rq.return_value = db_rows

        results = drive_coro(duplicate_service.find_duplicates(
            category="Potholes, damaged roads, footpaths",
            latitude=target_lat,
            longitude=target_lon,
            candidates=None,  # triggers Supabase query
        ))

        # Check call arguments
        assert mock_rq.call_count == 1
        args, kwargs = mock_rq.call_args
        assert args[0] == "complaints"
        params = kwargs.get("params", {})
        assert params.get("category") == "eq.Potholes, damaged roads, footpaths"
        assert "status" in params
        assert "in." in params["status"]

        # Only db-cand-001 should be within 100m
        assert len(results) == 1
        assert results[0]["complaint_id"] == "db-cand-001"
        assert results[0]["report_count"] == 5
        assert 25.0 < results[0]["distance_meters"] < 35.0

    print("PASS: Test 15 - Supabase candidate query end-to-end integration verified.")


if __name__ == "__main__":
    print("=" * 70)
    print("Running Member 3 Task M3-07 - Duplicate Detection Test Suite")
    print("=" * 70)

    test_01_same_category_within_100m()
    test_02_same_category_beyond_100m()
    test_03_different_category_identical_coords()
    test_04_missing_target_coords()
    test_05_invalid_target_and_candidate_coords()
    test_06_self_matching_prevention()
    test_07_multiple_matches_sorted_by_distance()
    test_08_resolved_and_rejected_filtering_active_only()
    test_09_active_only_false_includes_resolved()
    test_10_invalid_radius_values()
    test_11_supabase_query_failure()
    test_12_no_database_writes()
    test_13_no_personal_information_in_results()
    test_14_haversine_edge_cases()
    test_15_supabase_query_live_params()

    print("=" * 70)
    print("ALL 15 M3-07 TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
