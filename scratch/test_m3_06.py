import sys
import json
import base64
from unittest.mock import MagicMock, patch

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

def mock_field(default=..., **kwargs):
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
        if "description" in kwargs:
            desc = kwargs["description"]
            if not desc or not desc.strip():
                raise ValueError("Complaint description cannot be empty or whitespace only.")
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def model_validate(cls, data):
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
        # Enforce required response fields
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
        if not isinstance(sev, int) or sev < 1 or sev > 10:
            raise ValueError(f"Invalid severity: {sev}")
        if not isinstance(data["suggested_title"], str) or len(data["suggested_title"]) < 3:
            raise ValueError(f"Invalid suggested_title: {data.get('suggested_title')}")
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

sys.path.insert(0, 'backend')
from app.schemas.ai import AIAnalysisRequest, AIAnalysisResponse
from app.services.ai_service import AIService, ai_service
from app.core.config import settings

def make_gemini_response(json_text: str, status_code: int = 200):
    mock_resp = MagicMock(status_code=status_code)
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": json_text}
                    ]
                }
            }
        ]
    }
    return mock_resp

class MockDualClient:
    def __init__(self, post_resp=None, stream_resp=None, post_exc=None, stream_exc=None):
        self.post_resp = post_resp
        self.stream_resp = stream_resp
        self.post_exc = post_exc
        self.stream_exc = stream_exc
        self.post_calls = []
        self.stream_calls = []

    def __aenter__(self):
        return AwaitableVal(self)

    def __aexit__(self, exc_type, exc_val, exc_tb):
        return AwaitableVal(False)

    def post(self, url, *args, json=None, headers=None, **kwargs):
        self.post_calls.append({"url": url, "json": json, "headers": headers})
        if callable(self.post_exc):
            return AwaitableVal(exc=self.post_exc(len(self.post_calls)))
        if self.post_exc:
            return AwaitableVal(exc=self.post_exc)
        if callable(self.post_resp) and not isinstance(self.post_resp, MagicMock):
            return AwaitableVal(val=self.post_resp(len(self.post_calls)))
        return AwaitableVal(val=self.post_resp)

    def stream(self, method, url, headers=None, follow_redirects=False, **kwargs):
        self.stream_calls.append({"method": method, "url": url, "headers": headers, "follow_redirects": follow_redirects})
        if self.stream_exc:
            raise self.stream_exc
        return self.stream_resp

results = []

def run_test(name, fn):
    try:
        fn()
        results.append((name, 'PASS', ''))
    except Exception as e:
        results.append((name, 'FAIL', f"{type(e).__name__}: {e}"))

# 1. Missing API key
def test_1():
    with patch.object(settings, 'GEMINI_API_KEY', ''):
        srv = AIService()
        assert not srv.is_configured
        req = AIAnalysisRequest(description="Pothole on Main Street")
        resp = drive_coro(srv.analyze_complaint(req))
        assert resp.needs_human_review is True
        assert resp.department is None
        assert resp.category == "Other"
        assert "not configured" in resp.review_reason
run_test('1. Missing API key', test_1)

# 2. HTTP 429 Rate Limit
def test_2():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        client = MockDualClient(post_resp=MagicMock(status_code=429))
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="Pothole on Main Street")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.needs_human_review is True
            assert resp.department is None
            assert resp.category == "Other"
            assert "RuntimeError" in resp.review_reason
run_test('2. HTTP 429 Rate Limit', test_2)

# 3. HTTP 500 / 503 Provider Error
def test_3():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        client = MockDualClient(post_resp=MagicMock(status_code=503))
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="Streetlight broken")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.needs_human_review is True
            assert resp.department is None
            assert "RuntimeError" in resp.review_reason
run_test('3. HTTP 500 / 503 Provider Error', test_3)

# 4. Network Connection Failure
def test_4():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        client = MockDualClient(post_exc=httpx_mock.NetworkError("DNS resolution failed"))
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="Overflowing garbage")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.needs_human_review is True
            assert resp.department is None
            assert "RuntimeError" in resp.review_reason
run_test('4. Network Connection Failure', test_4)

# 5. Malformed Provider JSON (Unparseable HTTP Body)
def test_5():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        bad_resp = MagicMock(status_code=200)
        bad_resp.json.side_effect = ValueError("Invalid JSON in provider response")
        client = MockDualClient(post_resp=bad_resp)
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="Water leak on 2nd Ave")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.needs_human_review is True
            assert resp.department is None
            assert "RuntimeError" in resp.review_reason
run_test('5. Malformed Provider JSON', test_5)

# 6. Empty Candidates List from Provider
def test_6():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        bad_resp = MagicMock(status_code=200)
        bad_resp.json.return_value = {"candidates": []}
        client = MockDualClient(post_resp=bad_resp)
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="Water leak")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.needs_human_review is True
            assert resp.department is None
run_test('6. Empty Candidates List', test_6)

# 7. Malformed Model JSON Content
def test_7():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        client = MockDualClient(post_resp=make_gemini_response("{invalid json string:"))
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="Pothole")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.needs_human_review is True
            assert "valid JSON" in resp.review_reason
run_test('7. Malformed Model JSON Content', test_7)

# 8. Missing Required Response Fields
def test_8():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        # Missing 'suggested_title' and 'severity'
        incomplete_json = json.dumps({
            "category": "Potholes, damaged roads, footpaths",
            "issue_type": "Pothole",
            "department": "Public Works Department",
            "summary": "Pothole summary on road.",
            "recommended_action": "Repair pothole.",
            "language": "English",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })
        client = MockDualClient(post_resp=make_gemini_response(incomplete_json))
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="Pothole")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.needs_human_review is True
            assert resp.category == "Other"
            assert resp.department is None
            assert "Schema validation failed" in resp.review_reason
run_test('8. Missing Required Response Fields', test_8)

# 9. Invalid Category / Department
def test_9():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        invalid_cat_json = json.dumps({
            "suggested_title": "Alien Invasion on Road",
            "category": "Extraterrestrial Incident",  # Invalid category!
            "issue_type": "UFO",
            "department": "Public Works Department",
            "severity": 8,
            "summary": "UFO on road.",
            "recommended_action": "Investigate.",
            "language": "English",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })
        client = MockDualClient(post_resp=make_gemini_response(invalid_cat_json))
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="UFO sighting")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.needs_human_review is True
            assert resp.category == "Other"
            assert resp.department is None
run_test('9. Invalid Category / Department', test_9)

# 10. Severity Outside 1–10
def test_10():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        invalid_sev_json = json.dumps({
            "suggested_title": "Severe Pothole",
            "category": "Potholes, damaged roads, footpaths",
            "issue_type": "Pothole",
            "department": "Public Works Department",
            "severity": 99,  # Severity out of bounds!
            "summary": "Large pothole.",
            "recommended_action": "Fix.",
            "language": "English",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })
        client = MockDualClient(post_resp=make_gemini_response(invalid_sev_json))
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="Pothole")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.needs_human_review is True
            assert resp.severity == 5  # Fallback severity
run_test('10. Severity Outside 1–10', test_10)

# 11. Whitespace-Only Request Validation
def test_11():
    whitespace_descriptions = ["", "   ", "\t\t\n  \r\n"]
    for desc in whitespace_descriptions:
        caught = False
        try:
            AIAnalysisRequest(description=desc)
        except ValueError:
            caught = True
        assert caught, f"Expected whitespace description '{desc}' to be rejected"
run_test('11. Whitespace-Only Request Validation', test_11)

# 12. Safety Consistency: is_safety_related=False with non-null safety_category
def test_12():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        model_json = json.dumps({
            "suggested_title": "Streetlight Broken on 2nd St",
            "category": "Broken streetlights",
            "issue_type": "Broken Luminaire",
            "department": "Electrical Department",
            "severity": 4,
            "summary": "Streetlight is out on 2nd St.",
            "recommended_action": "Fix bulb.",
            "language": "English",
            "is_safety_related": False,  # Safety false...
            "safety_category": "Lighting issue",  # ...but category non-null!
            "needs_human_review": False,
            "review_reason": None
        })
        client = MockDualClient(post_resp=make_gemini_response(model_json))
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="Streetlight out on 2nd St.")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.is_safety_related is False
            # M3-06 Normalization Rule A: safety_category cleared to None!
            assert resp.safety_category is None
            assert resp.needs_human_review is False
run_test('12. Safety Consistency: False + non-null category', test_12)

# 13. Safety Consistency: is_safety_related=True with null safety_category
def test_13():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        model_json = json.dumps({
            "suggested_title": "Dark Transit Tunnel Hazard",
            "category": "Broken streetlights",
            "issue_type": "Dark Walkway",
            "department": "Electrical Department",
            "severity": 8,
            "summary": "Pedestrian tunnel has no lights, creating acute safety risk.",
            "recommended_action": "Emergency lighting restoration.",
            "language": "English",
            "is_safety_related": True,  # Safety true...
            "safety_category": None,  # ...but category null!
            "needs_human_review": False,
            "review_reason": None
        })
        client = MockDualClient(post_resp=make_gemini_response(model_json))
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="Pedestrian tunnel has no lights, women feel unsafe.")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.is_safety_related is True
            # M3-06 Normalization Rule A: safety_category set to 'Unverified safety concern'!
            assert resp.safety_category == "Unverified safety concern"
            assert resp.needs_human_review is False
run_test('13. Safety Consistency: True + null category', test_13)

# 14. Mandatory Human Review: department=None + needs_human_review=False
def test_14():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        model_json = json.dumps({
            "suggested_title": "Unclear Civic Issue on Crossroad",
            "category": "Potholes, damaged roads, footpaths",
            "issue_type": "Unclear Damage",
            "department": None,  # Department is None...
            "severity": 5,
            "summary": "Citizen reports unclear damage near crossroad.",
            "recommended_action": "Inspect site.",
            "language": "English",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,  # ...model forgot to set review flag!
            "review_reason": None
        })
        client = MockDualClient(post_resp=make_gemini_response(model_json))
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="Something broken on crossroad.")
            resp = drive_coro(srv.analyze_complaint(req))
            # M3-06 Normalization Rule B: forced needs_human_review=True!
            assert resp.needs_human_review is True
            assert resp.department is None
            assert resp.review_reason == "Unassigned civic complaint requires official department triage."
run_test('14. Mandatory Human Review: department=None', test_14)

# 15. Mandatory Human Review: category="Other" + needs_human_review=False
def test_15():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        model_json = json.dumps({
            "suggested_title": "Miscellaneous City Inquiry",
            "category": "Other",  # Category is Other...
            "issue_type": "Inquiry",
            "department": "Public Works Department",
            "severity": 4,
            "summary": "Citizen asking for city event dates.",
            "recommended_action": "Inform citizen.",
            "language": "English",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,  # ...model forgot to set review flag!
            "review_reason": None
        })
        client = MockDualClient(post_resp=make_gemini_response(model_json))
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="When is the city parade?")
            resp = drive_coro(srv.analyze_complaint(req))
            # M3-06 Normalization Rule B: forced needs_human_review=True!
            assert resp.needs_human_review is True
            assert resp.category == "Other"
            assert resp.review_reason == "Unassigned civic complaint requires official department triage."
run_test('15. Mandatory Human Review: category=Other', test_15)

# 16. Review Reason Completeness: needs_human_review=True with blank reason
def test_16():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        model_json = json.dumps({
            "suggested_title": "Damaged Footpath Section",
            "category": "Potholes, damaged roads, footpaths",
            "issue_type": "Footpath Crack",
            "department": "Public Works Department",
            "severity": 5,
            "summary": "Damaged footpath near market.",
            "recommended_action": "Repair footpath pavers.",
            "language": "English",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": True,  # Review requested...
            "review_reason": "   "  # ...but reason is whitespace!
        })
        client = MockDualClient(post_resp=make_gemini_response(model_json))
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="Footpath cracked near market.")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.needs_human_review is True
            # M3-06 Normalization Rule C: whitespace reason replaced with default triage reason!
            assert resp.review_reason == "Submission flagged for manual official triage."
run_test('16. Review Reason Completeness: blank reason filled', test_16)

# 17. Secret Hygiene: Error reasons do not leak credentials or internal URLs
def test_17():
    with patch.object(settings, 'GEMINI_API_KEY', 'super-secret-gemini-key-99999'), \
         patch.object(settings, 'SUPABASE_SERVICE_ROLE_KEY', 'super-secret-service-role-88888'):
        srv = AIService()
        # Simulate network error containing secret string in exception message
        secret_exc = httpx_mock.NetworkError("Failed to connect with super-secret-gemini-key-99999")
        client = MockDualClient(post_exc=secret_exc)
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="Pothole")
            resp = drive_coro(srv.analyze_complaint(req))
            assert "super-secret" not in resp.review_reason
            assert "99999" not in resp.review_reason
            assert "88888" not in resp.review_reason
            # Sanitized to generic exception type
            assert resp.review_reason == "Classification processing failure: RuntimeError"
run_test('17. Secret Hygiene in Error Reasons', test_17)

print('--- TEST SUMMARY ---')
all_passed = True
for name, status, err in results:
    msg = f' -> {err}' if err else ''
    print(f'[{status}] {name}{msg}')
    if status != 'PASS':
        all_passed = False

if all_passed:
    print('ALL 17 M3-06 TESTS PASSED')
else:
    print('SOME TESTS FAILED')
    sys.exit(1)
