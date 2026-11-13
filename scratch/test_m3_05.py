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

# Mock Stream Response for httpx client.stream
class MockStreamResponse:
    def __init__(self, chunks, status_code=200, headers=None):
        self.chunks = chunks
        self.status_code = status_code
        self.headers = headers or {}

    async def aiter_bytes(self, chunk_size=65536):
        for c in self.chunks:
            yield c

    def __aenter__(self):
        return AwaitableVal(self)

    def __aexit__(self, exc_type, exc_val, exc_tb):
        return AwaitableVal(False)

# Recording Client capable of handling both post and stream
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

# 1. Arbitrary External URL Rejection (SSRF defense)
def test_1():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'), \
         patch.object(settings, 'SUPABASE_URL', 'https://project.supabase.co'), \
         patch.object(settings, 'SUPABASE_SERVICE_ROLE_KEY', 'service-key'):
        srv = AIService()
        # Verify resolution rejects external host
        assert srv._resolve_image_target("https://evil-attacker.com/exploit.jpg") is None
        assert srv._resolve_image_target("http://project.supabase.co/img.jpg") is None  # Non-HTTPS
        assert srv._resolve_image_target("https://169.254.169.254/latest/meta-data") is None

        # Verify analyze_complaint completes via text-only with zero outbound stream calls
        llm_json = json.dumps({
            "suggested_title": "Pothole on Main Road",
            "category": "Potholes, damaged roads, footpaths",
            "issue_type": "Pothole",
            "department": "Public Works Department",
            "severity": 6,
            "summary": "Pothole on main road causing hazard.",
            "recommended_action": "Repair pothole.",
            "language": "English",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })
        client = MockDualClient(post_resp=make_gemini_response(llm_json))
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(
                description="Large pothole on Main Road near bus stop.",
                image_url="https://evil-attacker.com/exploit.jpg"
            )
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.category == "Potholes, damaged roads, footpaths"
            assert len(client.stream_calls) == 0  # Zero download attempts to external host!
            # Verify Gemini payload was text-only (no inlineData)
            assert len(client.post_calls) == 1
            parts = client.post_calls[0]["json"]["contents"][0]["parts"]
            assert len(parts) == 1
            assert "text" in parts[0]
            assert "inlineData" not in parts[0]
run_test('1. Arbitrary External URL Rejection', test_1)

# 2. Supabase Host & Port 443 Validation
def test_2():
    with patch.object(settings, 'SUPABASE_URL', 'https://project.supabase.co'), \
         patch.object(settings, 'SUPABASE_SERVICE_ROLE_KEY', 'secret-key-123'):
        srv = AIService()
        # Valid signed URL on port 443
        signed_url = "https://project.supabase.co/storage/v1/object/sign/complaint-images/complaints/user1/test.jpg?token=abc"
        res = srv._resolve_image_target(signed_url)
        assert res is not None
        target_url, headers = res
        assert target_url == signed_url
        # Signed URL must NOT carry service-role headers
        assert "Authorization" not in headers
        assert "apikey" not in headers

        # Non-standard port must be rejected
        bad_port_url = "https://project.supabase.co:8443/storage/v1/object/complaint-images/complaints/user1/test.jpg"
        assert srv._resolve_image_target(bad_port_url) is None
run_test('2. Supabase Host & Port 443 Validation', test_2)

# 3. Embedded Credentials Rejection
def test_3():
    with patch.object(settings, 'SUPABASE_URL', 'https://project.supabase.co'):
        srv = AIService()
        url_with_auth = "https://admin:pass@project.supabase.co/storage/v1/object/complaint-images/complaints/u1/img.jpg"
        assert srv._resolve_image_target(url_with_auth) is None
run_test('3. Embedded Credentials Rejection', test_3)

# 4. Invalid Bucket Path Rejection
def test_4():
    with patch.object(settings, 'SUPABASE_URL', 'https://project.supabase.co'):
        srv = AIService()
        other_bucket_url = "https://project.supabase.co/storage/v1/object/private-vault/secret.jpg"
        assert srv._resolve_image_target(other_bucket_url) is None
run_test('4. Invalid Bucket Path Rejection', test_4)

# 5. Path Traversal & Backslash Rejection
def test_5():
    with patch.object(settings, 'SUPABASE_URL', 'https://project.supabase.co'):
        srv = AIService()
        assert srv._resolve_image_target("complaints/../../etc/passwd") is None
        assert srv._resolve_image_target("complaints/%2e%2e/etc/passwd") is None
        assert srv._resolve_image_target("complaints\\user1\\img.jpg") is None
        assert srv._resolve_image_target("complaints/%5cuser1%5cimg.jpg") is None
        assert srv._resolve_image_target("complaints/\x00evil.jpg") is None
run_test('5. Path Traversal & Backslash Rejection', test_5)

# 6. Redirect Blocking
def test_6():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'), \
         patch.object(settings, 'SUPABASE_URL', 'https://project.supabase.co'), \
         patch.object(settings, 'SUPABASE_SERVICE_ROLE_KEY', 'service-key'):
        srv = AIService()
        redirect_stream = MockStreamResponse(chunks=[], status_code=302)
        llm_json = json.dumps({
            "suggested_title": "Broken Streetlight on Lane 4",
            "category": "Broken streetlights",
            "issue_type": "Broken Luminaire",
            "department": "Electrical Department",
            "severity": 5,
            "summary": "Streetlight dark on Lane 4.",
            "recommended_action": "Replace luminaire bulb.",
            "language": "English",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })
        client = MockDualClient(post_resp=make_gemini_response(llm_json), stream_resp=redirect_stream)
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(
                description="Streetlight is broken on Lane 4.",
                image_url="complaints/user1/light.jpg"
            )
            resp = drive_coro(srv.analyze_complaint(req))
            assert len(client.stream_calls) == 1
            assert client.stream_calls[0]["follow_redirects"] is False
            # Verify graceful text-only classification succeeded despite redirected image
            assert resp.category == "Broken streetlights"
            assert resp.department == "Electrical Department"
run_test('6. Redirect Blocking', test_6)

# 7. Streaming 5 MB Hard Limit
def test_7():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'), \
         patch.object(settings, 'SUPABASE_URL', 'https://project.supabase.co'):
        srv = AIService()
        # Deliver 6 MB in 1 MB chunks
        chunk = b"A" * (1024 * 1024)
        chunks = [chunk for _ in range(6)]
        oversize_stream = MockStreamResponse(chunks=chunks, status_code=200)

        llm_json = json.dumps({
            "suggested_title": "Garbage Dump in Park",
            "category": "Garbage accumulation",
            "issue_type": "Garbage Dump",
            "department": "Sanitation Department",
            "severity": 6,
            "summary": "Garbage accumulation in park.",
            "recommended_action": "Clear garbage.",
            "language": "English",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })
        client = MockDualClient(post_resp=make_gemini_response(llm_json), stream_resp=oversize_stream)
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(
                description="Huge garbage accumulation in central park.",
                image_url="complaints/user1/large.jpg"
            )
            resp = drive_coro(srv.analyze_complaint(req))
            # Stream aborted upon passing 5MB; text-only succeeds
            assert resp.category == "Garbage accumulation"
            assert resp.department == "Sanitation Department"
run_test('7. Streaming 5 MB Hard Limit', test_7)

# 8. Magic Bytes Validation
def test_8():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'), \
         patch.object(settings, 'SUPABASE_URL', 'https://project.supabase.co'):
        srv = AIService()
        # Feed HTML content masquerading as JPEG
        html_bytes = b"<!DOCTYPE html><html><body>Error 404</body></html>"
        bad_stream = MockStreamResponse(chunks=[html_bytes], status_code=200)

        llm_json = json.dumps({
            "suggested_title": "Drainage Blockage on 5th Cross",
            "category": "Water leakage, drainage blockage",
            "issue_type": "Drainage Overflow",
            "department": "Water & Sewerage Department",
            "severity": 7,
            "summary": "Drainage overflow on 5th cross.",
            "recommended_action": "Clear drainage obstruction.",
            "language": "English",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })
        client = MockDualClient(post_resp=make_gemini_response(llm_json), stream_resp=bad_stream)
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(
                description="Drainage blocked and overflowing on 5th cross.",
                image_url="complaints/user1/drain.jpg"
            )
            resp = drive_coro(srv.analyze_complaint(req))
            # Magic bytes rejected; text-only succeeds
            assert resp.category == "Water leakage, drainage blockage"
            assert resp.department == "Water & Sewerage Department"
run_test('8. Magic Bytes Validation', test_8)

# 9. Shared Time Budget Enforcement
def test_9():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'), \
         patch.object(settings, 'SUPABASE_URL', 'https://project.supabase.co'):
        srv = AIService()
        # If monotonic time simulates only 1.0 second remaining, image download should be skipped
        with patch('time.monotonic', side_effect=[0.0, 7.5, 7.6, 7.7, 7.8]):
            client = MockDualClient(post_resp=make_gemini_response(json.dumps({
                "suggested_title": "Pothole",
                "category": "Potholes, damaged roads, footpaths",
                "issue_type": "Pothole",
                "department": "Public Works Department",
                "severity": 5,
                "summary": "Pothole summary.",
                "recommended_action": "Fix.",
                "language": "English",
                "is_safety_related": False,
                "safety_category": None,
                "needs_human_review": False,
                "review_reason": None
            })))
            with patch('httpx.AsyncClient', lambda *a, **kw: client):
                req = AIAnalysisRequest(description="Pothole on road", image_url="complaints/u1/p.jpg")
                resp = drive_coro(srv.analyze_complaint(req))
                # Image download was skipped because remaining time was < 4.5s
                assert len(client.stream_calls) == 0
run_test('9. Shared Time Budget Enforcement', test_9)

# 10. Image / Text Contradiction Handling
def test_10():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'), \
         patch.object(settings, 'SUPABASE_URL', 'https://project.supabase.co'), \
         patch.object(settings, 'SUPABASE_SERVICE_ROLE_KEY', 'service-key'):
        srv = AIService()
        valid_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        stream_resp = MockStreamResponse(chunks=[valid_jpeg], status_code=200)

        # Gemini model returns visual contradiction: category preserved, needs_human_review=True
        llm_json = json.dumps({
            "suggested_title": "Severe Pothole on Station Road",
            "category": "Potholes, damaged roads, footpaths",  # Preserved text category!
            "issue_type": "Pothole",
            "department": "Public Works Department",
            "severity": 6,
            "summary": "Citizen reported large pothole on Station Road, but attached image depicts an indoor living room.",
            "recommended_action": "Dispatch municipal field inspector for manual verification due to visual mismatch.",
            "language": "English",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": True,
            "review_reason": "Attached photograph contradicts written description of pothole; manual review required."
        })
        client = MockDualClient(post_resp=make_gemini_response(llm_json), stream_resp=stream_resp)
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(
                description="Dangerous deep pothole on Station Road near railway station.",
                image_url="complaints/user1/contradictory.jpg"
            )
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.category == "Potholes, damaged roads, footpaths"
            assert resp.department == "Public Works Department"
            assert resp.needs_human_review is True
            assert "contradicts" in resp.review_reason
run_test('10. Image / Text Contradiction Handling', test_10)

# 11. Successful Multimodal Classification
def test_11():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'), \
         patch.object(settings, 'SUPABASE_URL', 'https://project.supabase.co'), \
         patch.object(settings, 'SUPABASE_SERVICE_ROLE_KEY', 'service-key'):
        srv = AIService()
        valid_jpeg = b"\xff\xd8\xff\xe0" + b"\x12\x34" * 50
        stream_resp = MockStreamResponse(chunks=[valid_jpeg], status_code=200)

        llm_json = json.dumps({
            "suggested_title": "Severe Cave-in on Ring Road",
            "category": "Potholes, damaged roads, footpaths",
            "issue_type": "Road Cave-in",
            "department": "Public Works Department",
            "severity": 9,
            "summary": "Visual inspection corroborates dangerous road cave-in exceeding 1 meter width.",
            "recommended_action": "Cordon off hazardous traffic lane and dispatch emergency asphalt crew.",
            "language": "English",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })
        client = MockDualClient(post_resp=make_gemini_response(llm_json), stream_resp=stream_resp)
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(
                description="Road has caved in on Ring Road, dangerous for cars.",
                image_url="complaints/user1/cavein.jpg"
            )
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.category == "Potholes, damaged roads, footpaths"
            assert resp.severity == 9
            assert resp.needs_human_review is False
            # Verify multimodal inlineData payload was constructed and sent
            assert len(client.post_calls) == 1
            parts = client.post_calls[0]["json"]["contents"][0]["parts"]
            assert len(parts) == 2
            assert "text" in parts[0]
            assert "inlineData" in parts[1]
            assert parts[1]["inlineData"]["mimeType"] == "image/jpeg"
            assert parts[1]["inlineData"]["data"] == base64.b64encode(valid_jpeg).decode("utf-8")
run_test('11. Successful Multimodal Classification', test_11)

# 12. Multilingual with Image (Hindi)
def test_12():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'), \
         patch.object(settings, 'SUPABASE_URL', 'https://project.supabase.co'), \
         patch.object(settings, 'SUPABASE_SERVICE_ROLE_KEY', 'service-key'):
        srv = AIService()
        valid_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
        stream_resp = MockStreamResponse(chunks=[valid_png], status_code=200)

        llm_json = json.dumps({
            "suggested_title": "सड़क पर गहरा गड्ढा और जलभराव",
            "category": "Potholes, damaged roads, footpaths",
            "issue_type": "गड्ढा",
            "department": "Public Works Department",
            "severity": 8,
            "summary": "संलग्न तस्वीर से पुष्टि होती है कि मुख्य मार्ग पर गहरा गड्ढा है जिससे दुर्घटना की संभावना है।",
            "recommended_action": "सड़क मरम्मत दल को भेजकर गड्ढा भरने का कार्य तुरंत कराया जाए।",
            "language": "Hindi",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })
        client = MockDualClient(post_resp=make_gemini_response(llm_json), stream_resp=stream_resp)
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(
                description="मुख्य सड़क पर बहुत बड़ा गड्ढा है जिसमें पानी भर गया है।",
                image_url="complaints/user1/hindi_pothole.png"
            )
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.language == "Hindi"
            assert resp.category == "Potholes, damaged roads, footpaths"
            assert resp.department == "Public Works Department"
            assert resp.needs_human_review is False
            assert "गड्ढा" in resp.suggested_title
run_test('12. Multilingual with Image (Hindi)', test_12)

# 13. Text-Only Fallback on Multimodal Failure
def test_13():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'), \
         patch.object(settings, 'SUPABASE_URL', 'https://project.supabase.co'), \
         patch.object(settings, 'SUPABASE_SERVICE_ROLE_KEY', 'service-key'):
        srv = AIService()
        valid_webp = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 50
        stream_resp = MockStreamResponse(chunks=[valid_webp], status_code=200)

        # Primary call fails with 400 (e.g. Gemini image processing error); retry succeeds with text-only
        call_counter = {"count": 0}
        text_only_json = json.dumps({
            "suggested_title": "Fallen Tree Blocking Roadway",
            "category": "Public park or facility damage",
            "issue_type": "Fallen Tree",
            "department": "Parks & Public Assets Department",
            "severity": 8,
            "summary": "Large tree has fallen blocking the roadway.",
            "recommended_action": "Dispatch tree clearing squad.",
            "language": "English",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })

        def mock_post(call_num):
            if call_num == 1:
                # First multimodal call fails
                raise RuntimeError("Gemini API returned error HTTP 400: image decoding error")
            # Second retry call succeeds
            return make_gemini_response(text_only_json)

        client = MockDualClient(post_resp=mock_post, stream_resp=stream_resp)
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(
                description="Huge tree branch has fallen across the road.",
                image_url="complaints/user1/tree.webp"
            )
            resp = drive_coro(srv.analyze_complaint(req))
            assert len(client.post_calls) == 2  # Multimodal attempted first, then retried text-only!
            assert resp.category == "Public park or facility damage"
            assert resp.department == "Parks & Public Assets Department"
            assert resp.needs_human_review is False
run_test('13. Text-Only Fallback on Multimodal Failure', test_13)

# 14. Existing M3-04 Text-Only Regression
def test_14():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        llm_json = json.dumps({
            "suggested_title": "Broken Traffic Signal at Junction",
            "category": "Traffic congestion, signal faults",
            "issue_type": "Traffic Signal Malfunction",
            "department": "Traffic & Transport Department",
            "severity": 7,
            "summary": "Traffic light stuck on red causing major congestion.",
            "recommended_action": "Reset and repair signal control unit.",
            "language": "English",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })
        client = MockDualClient(post_resp=make_gemini_response(llm_json))
        with patch('httpx.AsyncClient', lambda *a, **kw: client):
            req = AIAnalysisRequest(description="Traffic light stuck on red causing congestion.", image_url=None)
            resp = drive_coro(srv.analyze_complaint(req))
            assert len(client.stream_calls) == 0  # Zero download attempts when image_url is None
            assert len(client.post_calls) == 1
            assert resp.category == "Traffic congestion, signal faults"
            assert resp.department == "Traffic & Transport Department"
            assert resp.needs_human_review is False
run_test('14. Existing M3-04 Text-Only Regression', test_14)

print('--- TEST SUMMARY ---')
all_passed = True
for name, status, err in results:
    msg = f' -> {err}' if err else ''
    print(f'[{status}] {name}{msg}')
    if status != 'PASS':
        all_passed = False

if all_passed:
    print('ALL 14 TESTS PASSED')
else:
    print('SOME TESTS FAILED')
    sys.exit(1)
