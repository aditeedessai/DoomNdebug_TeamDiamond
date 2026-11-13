import sys
import json
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
        return classmethod(fn)
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
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def model_validate(cls, data):
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
        if "category" in data and data["category"] not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category: {data['category']}")
        if "department" in data and data["department"] not in VALID_DEPARTMENTS:
            raise ValueError(f"Invalid department: {data['department']}")
        if "language" in data and data["language"] not in VALID_LANGUAGES:
            raise ValueError(f"Invalid language: {data['language']}")
        if "safety_category" in data and data["safety_category"] not in VALID_SAFETY_CATEGORIES:
            raise ValueError(f"Invalid safety_category: {data['safety_category']}")
        if "severity" in data:
            sev = data["severity"]
            if not isinstance(sev, int) or sev < 1 or sev > 10:
                raise ValueError(f"Invalid severity: {sev}")
        return cls(**data)

    def model_dump(self):
        return self.__dict__

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

class RecordingAsyncClient:
    def __init__(self, post_resp=None, post_exc=None):
        self.post_resp = post_resp
        self.post_exc = post_exc
        self.calls = []

    def __aenter__(self):
        return AwaitableVal(self)

    def __aexit__(self, exc_type, exc_val, exc_tb):
        return AwaitableVal(False)

    def post(self, url, *args, json=None, headers=None, **kwargs):
        self.calls.append({"url": url, "json": json, "headers": headers})
        if self.post_exc:
            return AwaitableVal(exc=self.post_exc)
        return AwaitableVal(val=self.post_resp)

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

results = []

def run_test(name, fn):
    try:
        fn()
        results.append((name, 'PASS', ''))
    except Exception as e:
        results.append((name, 'FAIL', f"{type(e).__name__}: {e}"))

# 1. Correct Gemini 3.5 Flash endpoint and model ID
def test_1():
    assert AIService.DEFAULT_MODEL == "gemini-3.5-flash"
    assert ai_service.model_name == "gemini-3.5-flash"
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key-35'):
        srv = AIService()
        assert srv.model_name == "gemini-3.5-flash"
        client = RecordingAsyncClient(post_resp=make_gemini_response(json.dumps({
            "suggested_title": "Pothole on Main Road",
            "category": "Potholes, damaged roads, footpaths",
            "issue_type": "Pothole",
            "department": "Public Works Department",
            "severity": 6,
            "summary": "Pothole on road.",
            "recommended_action": "Repair road.",
            "language": "English",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })))
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="Pothole on the road")
            resp = drive_coro(srv.analyze_complaint(req))
            assert len(client.calls) == 1
            call = client.calls[0]
            # Verify endpoint URL has gemini-3.5-flash
            expected_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent"
            assert call["url"] == expected_endpoint, f"Expected {expected_endpoint}, got {call['url']}"
            # Verify headers
            assert call["headers"]["X-goog-api-key"] == "test-key-35"
            # Verify generationConfig has responseMimeType and temperature is omitted
            gen_config = call["json"].get("generationConfig", {})
            assert gen_config.get("responseMimeType") == "application/json"
            assert "temperature" not in gen_config, f"temperature should be omitted for gemini-3.5-flash, found: {gen_config}"
run_test('1. Correct Gemini 3.5 Flash endpoint and model ID', test_1)

# 2. English complaint classification
def test_2():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key-35'):
        srv = AIService()
        llm_json = json.dumps({
            "suggested_title": "Severe Pothole on Station Road",
            "category": "Potholes, damaged roads, footpaths",
            "issue_type": "Pothole",
            "department": "Public Works Department",
            "severity": 7,
            "summary": "Large pothole causing vehicle damage near Station Road.",
            "recommended_action": "Dispatch asphalt patch repair squad.",
            "language": "English",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })
        client = RecordingAsyncClient(post_resp=make_gemini_response(llm_json))
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="Severe pothole on Station Road causing vehicle damage.")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.language == "English"
            assert resp.category == "Potholes, damaged roads, footpaths"
            assert resp.department == "Public Works Department"
            assert resp.severity == 7
            assert resp.needs_human_review is False
run_test('2. English complaint classification', test_2)

# 3. Hindi complaint classification (Devanagari)
def test_3():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key-35'):
        srv = AIService()
        llm_json = json.dumps({
            "suggested_title": "मुख्य बाजार में कचरे का ढेर",
            "category": "Garbage accumulation",
            "issue_type": "कचरे का ढेर",
            "department": "Sanitation Department",
            "severity": 6,
            "summary": "मुख्य बाजार के प्रवेश द्वार पर कचरे का बड़ा ढेर जमा है।",
            "recommended_action": "सफाई वाहन भेजकर कचरा तुरंत साफ कराया जाए।",
            "language": "Hindi",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })
        client = RecordingAsyncClient(post_resp=make_gemini_response(llm_json))
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="मुख्य बाजार के प्रवेश द्वार पर बहुत कचरा पड़ा है।")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.language == "Hindi"
            assert resp.category == "Garbage accumulation"
            assert resp.department == "Sanitation Department"
            assert resp.needs_human_review is False
            assert "कचरे" in resp.suggested_title
run_test('3. Hindi complaint classification', test_3)

# 4. Hinglish complaint classification
def test_4():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key-35'):
        srv = AIService()
        llm_json = json.dumps({
            "suggested_title": "Main Road par Streetlight Band",
            "category": "Broken streetlights",
            "issue_type": "Streetlight Defect",
            "department": "Electrical Department",
            "severity": 5,
            "summary": "Main road par streetlight band hai jiski wajah se andhera ho raha hai.",
            "recommended_action": "Electrical maintenance team bulb change kare.",
            "language": "Hindi",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })
        client = RecordingAsyncClient(post_resp=make_gemini_response(llm_json))
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="Main road par streetlight band hai, bohot andhera rehta hai.")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.language == "Hindi"
            assert resp.category == "Broken streetlights"
            assert resp.department == "Electrical Department"
            assert resp.needs_human_review is False
run_test('4. Hinglish complaint classification', test_4)

# 5. Safety-related complaint classification
def test_5():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key-35'):
        srv = AIService()
        llm_json = json.dumps({
            "suggested_title": "Dark Pedestrian Underpass at Metro",
            "category": "Broken streetlights",
            "issue_type": "Unlit Walkway",
            "department": "Electrical Department",
            "severity": 8,
            "summary": "Unlit pedestrian walkway near metro station causing serious safety risk for women commuters.",
            "recommended_action": "Urgent electrical restoration of luminaire fixtures along pedestrian underpass.",
            "language": "English",
            "is_safety_related": True,
            "safety_category": "Lighting issue",
            "needs_human_review": False,
            "review_reason": None
        })
        client = RecordingAsyncClient(post_resp=make_gemini_response(llm_json))
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="Pedestrian underpass near metro is pitch black at night, women commuters feel very unsafe.")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.is_safety_related is True
            assert resp.safety_category == "Lighting issue"
            assert resp.severity == 8
            assert resp.needs_human_review is False
run_test('5. Safety-related complaint classification', test_5)

# 6. Structured JSON response extraction (including markdown fence stripping)
def test_6():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key-35'):
        srv = AIService()
        fenced_json = "```json\n" + json.dumps({
            "suggested_title": "Water Pipeline Leak on MG Road",
            "category": "Water leakage, drainage blockage",
            "issue_type": "Water Leakage",
            "department": "Water & Sewerage Department",
            "severity": 7,
            "summary": "Clean drinking water leaking from underground pipe on MG Road.",
            "recommended_action": "Excavate and patch leaking pipe section.",
            "language": "English",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        }) + "\n```"
        client = RecordingAsyncClient(post_resp=make_gemini_response(fenced_json))
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="Clean water is leaking from a pipe under MG Road.")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.category == "Water leakage, drainage blockage"
            assert resp.department == "Water & Sewerage Department"
            assert resp.needs_human_review is False
run_test('6. Structured JSON response extraction', test_6)

# 7. Malformed JSON fallback
def test_7():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key-35'):
        srv = AIService()
        client = RecordingAsyncClient(post_resp=make_gemini_response("{this is broken json: [}"))
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="Broken pipe leaking water everywhere")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.category == "Other"
            assert resp.department is None
            assert resp.needs_human_review is True
            assert "valid JSON" in resp.review_reason
run_test('7. Malformed JSON fallback', test_7)

# 8. Missing API key fallback
def test_8():
    with patch.object(settings, 'GEMINI_API_KEY', ''):
        srv = AIService()
        assert srv.is_configured is False
        req = AIAnalysisRequest(description="Pothole on Main Road")
        resp = drive_coro(srv.analyze_complaint(req))
        assert resp.category == "Other"
        assert resp.department is None
        assert resp.needs_human_review is True
        assert "not configured" in resp.review_reason
run_test('8. Missing API key fallback', test_8)

# 9. Timeout fallback
def test_9():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key-35'):
        srv = AIService()
        client = RecordingAsyncClient(post_exc=httpx_mock.TimeoutException("Request timed out"))
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="Streetlight broken")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.category == "Other"
            assert resp.department is None
            assert resp.needs_human_review is True
run_test('9. Timeout fallback', test_9)

# 10. Invalid model response structure fallback (e.g. empty candidates or wrong data type)
def test_10():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key-35'):
        srv = AIService()
        # Mock response with empty candidates list
        bad_resp = MagicMock(status_code=200)
        bad_resp.json.return_value = {"candidates": []}
        client = RecordingAsyncClient(post_resp=bad_resp)
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="Fallen tree blocking lane")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.category == "Other"
            assert resp.department is None
            assert resp.needs_human_review is True
run_test('10. Invalid model response fallback', test_10)

print('--- TEST SUMMARY ---')
all_passed = True
for name, status, err in results:
    msg = f' -> {err}' if err else ''
    print(f'[{status}] {name}{msg}')
    if status != 'PASS':
        all_passed = False

if all_passed:
    print('ALL 10 TESTS PASSED')
else:
    print('SOME TESTS FAILED')
    sys.exit(1)
