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
        # Validate literal fields if present on response
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

class MockAsyncClient:
    def __init__(self, *args, post_resp=None, post_exc=None, **kwargs):
        self.post_resp = post_resp
        self.post_exc = post_exc
    def __aenter__(self):
        return AwaitableVal(self)
    def __aexit__(self, exc_type, exc_val, exc_tb):
        return AwaitableVal(False)
    def post(self, *args, **kwargs):
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

# 1. English pothole complaint
def test_1():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        llm_json = json.dumps({
            "suggested_title": "Deep Pothole on Station Road",
            "category": "Potholes, damaged roads, footpaths",
            "issue_type": "Pothole",
            "department": "Public Works Department",
            "severity": 8,
            "summary": "Deep pothole causing traffic obstruction on Station Road.",
            "recommended_action": "Deploy rapid road patch crew to inspect and repair pothole.",
            "language": "English",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })
        mock_factory = lambda *args, **kwargs: MockAsyncClient(post_resp=make_gemini_response(llm_json))
        with patch('httpx.AsyncClient', mock_factory):
            req = AIAnalysisRequest(description="Large dangerous pothole on Station Road near the traffic signal.")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.language == "English"
            assert resp.category == "Potholes, damaged roads, footpaths"
            assert resp.department == "Public Works Department"
            assert resp.needs_human_review is False
run_test('1. English pothole complaint', test_1)

# 2. Hindi pothole complaint (Devanagari)
def test_2():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        llm_json = json.dumps({
            "suggested_title": "एमजी रोड पर गहरा गड्ढा",
            "category": "Potholes, damaged roads, footpaths",
            "issue_type": "गड्ढा",
            "department": "Public Works Department",
            "severity": 8,
            "summary": "एमजी रोड पर बस स्टैंड के पास गहरा गड्ढा है जिससे दोपहिया वाहन फिसल रहे हैं।",
            "recommended_action": "सड़क मरम्मत दल को भेजकर गड्ढा भरने का कार्य तुरंत कराया जाए।",
            "language": "Hindi",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })
        mock_factory = lambda *args, **kwargs: MockAsyncClient(post_resp=make_gemini_response(llm_json))
        with patch('httpx.AsyncClient', mock_factory):
            req = AIAnalysisRequest(description="एमजी रोड पर बस स्टैंड के पास गहरा गड्ढा है जिससे गाड़ियाँ फिसल रही हैं।")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.language == "Hindi"
            assert resp.category == "Potholes, damaged roads, footpaths"
            assert resp.department == "Public Works Department"
            # Crucial M3-04 requirement: Hindi alone does NOT force human review!
            assert resp.needs_human_review is False
            assert "गड्ढा" in resp.suggested_title
            assert "गड्ढा" in resp.summary
run_test('2. Hindi pothole complaint', test_2)

# 3. Hindi garbage complaint
def test_3():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        llm_json = json.dumps({
            "suggested_title": "वार्ड 4 में कचरे का ढेर",
            "category": "Garbage accumulation",
            "issue_type": "कचरे का ढेर",
            "department": "Sanitation Department",
            "severity": 6,
            "summary": "वार्ड 4 की मुख्य सड़क पर कचरे का बड़ा ढेर लगा है जिससे भारी दुर्गंध आ रही है।",
            "recommended_action": "सफाई वाहन भेजकर संचित कचरा तुरंत हटवाया जाए।",
            "language": "Hindi",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })
        mock_factory = lambda *args, **kwargs: MockAsyncClient(post_resp=make_gemini_response(llm_json))
        with patch('httpx.AsyncClient', mock_factory):
            req = AIAnalysisRequest(description="वार्ड 4 में सड़क किनारे कचरे का बड़ा ढेर लगा है, बहुत दुर्गंध आ रही है।")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.language == "Hindi"
            assert resp.category == "Garbage accumulation"
            assert resp.department == "Sanitation Department"
            assert resp.needs_human_review is False
            assert "कचरे" in resp.suggested_title
run_test('3. Hindi garbage complaint', test_3)

# 4. Hindi broken streetlight complaint
def test_4():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        llm_json = json.dumps({
            "suggested_title": "घर के सामने बंद स्ट्रीट लाइट",
            "category": "Broken streetlights",
            "issue_type": "स्ट्रीट लाइट खराब",
            "department": "Electrical Department",
            "severity": 4,
            "summary": "आवासीय मकान के सामने स्ट्रीट लाइट पिछले कई दिनों से बंद पड़ी है।",
            "recommended_action": "विद्युत रखरखाव दल को भेजकर बल्ब और वायरिंग की जांच की जाए।",
            "language": "Hindi",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })
        mock_factory = lambda *args, **kwargs: MockAsyncClient(post_resp=make_gemini_response(llm_json))
        with patch('httpx.AsyncClient', mock_factory):
            req = AIAnalysisRequest(description="हमारे घर के सामने वाली स्ट्रीट लाइट कई दिनों से खराब पड़ी है।")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.language == "Hindi"
            assert resp.category == "Broken streetlights"
            assert resp.department == "Electrical Department"
            assert resp.is_safety_related is False
            assert resp.needs_human_review is False
run_test('4. Hindi broken streetlight complaint', test_4)

# 5. Hinglish pothole complaint
def test_5():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        llm_json = json.dumps({
            "suggested_title": "Main Road par Pothole aur Traffic Jam",
            "category": "Potholes, damaged roads, footpaths",
            "issue_type": "Pothole",
            "department": "Public Works Department",
            "severity": 7,
            "summary": "Main road par bohot bada pothole hai jiski wajah se traffic jam aur do-pahiyavahan slip ho rahe hain.",
            "recommended_action": "Road maintenance crew ko bhejkar asphalt patching karya turant karwaya jaye.",
            "language": "Hindi",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })
        mock_factory = lambda *args, **kwargs: MockAsyncClient(post_resp=make_gemini_response(llm_json))
        with patch('httpx.AsyncClient', mock_factory):
            req = AIAnalysisRequest(description="Main road par bohot bada pothole hai, traffic jam ho raha hai aur bikes slip ho rahi hain.")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.language == "Hindi"
            assert resp.category == "Potholes, damaged roads, footpaths"
            assert resp.department == "Public Works Department"
            assert resp.needs_human_review is False
run_test('5. Hinglish pothole complaint', test_5)

# 6. English complaint with language_hint="hi"
def test_6():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        llm_json = json.dumps({
            "suggested_title": "Overflowing Trash Bins near Market",
            "category": "Garbage accumulation",
            "issue_type": "Overflowing Bins",
            "department": "Sanitation Department",
            "severity": 6,
            "summary": "Overflowing garbage bins outside main market entrance causing odor.",
            "recommended_action": "Dispatch sanitation collection truck.",
            "language": "English",  # Model correctly prioritized actual text over incorrect hint!
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })
        mock_factory = lambda *args, **kwargs: MockAsyncClient(post_resp=make_gemini_response(llm_json))
        with patch('httpx.AsyncClient', mock_factory):
            req = AIAnalysisRequest(description="Overflowing trash bins near the market causing odor.", language_hint="hi")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.language == "English"
            assert resp.category == "Garbage accumulation"
            assert resp.needs_human_review is False
run_test('6. English complaint with language_hint="hi"', test_6)

# 7. Hindi complaint with language_hint="en"
def test_7():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        llm_json = json.dumps({
            "suggested_title": "सड़क पर गंदा पानी बह रहा है",
            "category": "Water leakage, drainage blockage",
            "issue_type": "सीवर का पानी",
            "department": "Water & Sewerage Department",
            "severity": 7,
            "summary": "मुख्य सड़क पर सीवर लाइन से गंदा पानी बह रहा है।",
            "recommended_action": "जल एवं सीवरेज विभाग द्वारा सीवर लाइन की सफाई कराई जाए।",
            "language": "Hindi",  # Model correctly prioritized actual Devanagari text over incorrect hint!
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })
        mock_factory = lambda *args, **kwargs: MockAsyncClient(post_resp=make_gemini_response(llm_json))
        with patch('httpx.AsyncClient', mock_factory):
            req = AIAnalysisRequest(description="सड़क पर गंदा पानी बह रहा है सीवर ब्लॉक हो गया है", language_hint="en")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.language == "Hindi"
            assert resp.category == "Water leakage, drainage blockage"
            assert resp.department == "Water & Sewerage Department"
            assert resp.needs_human_review is False
run_test('7. Hindi complaint with language_hint="en"', test_7)

# 8. Very short Hindi complaint
def test_8():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        llm_json = json.dumps({
            "suggested_title": "सड़क का गड्ढा",
            "category": "Potholes, damaged roads, footpaths",
            "issue_type": "गड्ढा",
            "department": "Public Works Department",
            "severity": 5,
            "summary": "एक शब्द का विवरण जिसमें स्थान का उल्लेख नहीं है।",
            "recommended_action": "नागरिक से सटीक स्थान की जानकारी मांगी जाए।",
            "language": "Hindi",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": True,
            "review_reason": "विवरण बहुत संक्षिप्त है और इसमें स्थान की जानकारी नहीं है।"
        })
        mock_factory = lambda *args, **kwargs: MockAsyncClient(post_resp=make_gemini_response(llm_json))
        with patch('httpx.AsyncClient', mock_factory):
            req = AIAnalysisRequest(description="गड्ढा")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.language == "Hindi"
            assert resp.needs_human_review is True
run_test('8. Very short Hindi complaint', test_8)

# 9. Gibberish Hindi text
def test_9():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        llm_json = json.dumps({
            "suggested_title": "अस्पष्ट प्रविष्टि (समीक्षा लंबित)",
            "category": "Other",
            "issue_type": "अस्पष्ट पाठ",
            "department": None,
            "severity": 5,
            "summary": "विवरण में अर्थहीन वर्णमाला अनुक्रम दिया गया है।",
            "recommended_action": "प्रविष्टि की मैन्युअल समीक्षा की जाए।",
            "language": "Hindi",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": True,
            "review_reason": "Submission is gibberish or unclassifiable."
        })
        mock_factory = lambda *args, **kwargs: MockAsyncClient(post_resp=make_gemini_response(llm_json))
        with patch('httpx.AsyncClient', mock_factory):
            req = AIAnalysisRequest(description="कखगघ चछजझ टठडढ तथरद")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.category == "Other"
            assert resp.department is None
            assert resp.needs_human_review is True
run_test('9. Gibberish Hindi text', test_9)

# 10. Non-civic Hindi submission
def test_10():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        llm_json = json.dumps({
            "suggested_title": "गैर-नागरिक अनुरोध",
            "category": "Other",
            "issue_type": "गैर-नागरिक विषय",
            "department": None,
            "severity": 5,
            "summary": "उपयोगकर्ता द्वारा कविता सुनाने का अनुरोध किया गया है, जो नगर निगम के दायरे से बाहर है।",
            "recommended_action": "गैर-नागरिक विषय मानकर फ़ाइल बंद करें।",
            "language": "Hindi",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": True,
            "review_reason": "Submission is outside municipal complaint management scope."
        })
        mock_factory = lambda *args, **kwargs: MockAsyncClient(post_resp=make_gemini_response(llm_json))
        with patch('httpx.AsyncClient', mock_factory):
            req = AIAnalysisRequest(description="मुझे एक अच्छी कविता सुनाइए")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.category == "Other"
            assert resp.department is None
            assert resp.needs_human_review is True
run_test('10. Non-civic Hindi submission', test_10)

# 11. Hindi safety-related complaint
def test_11():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        llm_json = json.dumps({
            "suggested_title": "बस स्टॉप पैदल मार्ग पर बंद लाइटें",
            "category": "Broken streetlights",
            "issue_type": "पैदल मार्ग पर अंधेरा",
            "department": "Electrical Department",
            "severity": 8,
            "summary": "बस स्टॉप के पास पैदल रास्ते पर लाइटें बंद हैं, जिससे रात में महिलाओं के लिए असुरक्षा उत्पन्न हो रही है।",
            "recommended_action": "विद्युत विभाग तुरंत लाइटें चालू करे ताकि पैदल यात्रियों की सुरक्षा सुनिश्चित हो सके।",
            "language": "Hindi",
            "is_safety_related": True,
            "safety_category": "Lighting issue",
            "needs_human_review": False,
            "review_reason": None
        })
        mock_factory = lambda *args, **kwargs: MockAsyncClient(post_resp=make_gemini_response(llm_json))
        with patch('httpx.AsyncClient', mock_factory):
            req = AIAnalysisRequest(description="बस स्टॉप के पास पैदल रास्ते पर लाइटें बंद हैं, रात में महिलाओं के लिए बहुत असुरक्षित है।")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.language == "Hindi"
            assert resp.category == "Broken streetlights"
            assert resp.department == "Electrical Department"
            assert resp.is_safety_related is True
            assert resp.safety_category == "Lighting issue"
            assert resp.severity == 8
            assert resp.needs_human_review is False
run_test('11. Hindi safety-related complaint', test_11)

# 12. English regression test
def test_12():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        llm_json = json.dumps({
            "suggested_title": "Water Pipe Burst on Central Road",
            "category": "Water leakage, drainage blockage",
            "issue_type": "Water Main Leak",
            "department": "Water & Sewerage Department",
            "severity": 8,
            "summary": "Drinking water main pipe has burst and is flooding the road.",
            "recommended_action": "Dispatch emergency water pipeline repair squad.",
            "language": "English",
            "is_safety_related": False,
            "safety_category": None,
            "needs_human_review": False,
            "review_reason": None
        })
        mock_factory = lambda *args, **kwargs: MockAsyncClient(post_resp=make_gemini_response(llm_json))
        with patch('httpx.AsyncClient', mock_factory):
            req = AIAnalysisRequest(description="Drinking water main pipe has burst and is flooding Central Road.")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.language == "English"
            assert resp.category == "Water leakage, drainage blockage"
            assert resp.department == "Water & Sewerage Department"
            assert resp.severity == 8
            assert resp.needs_human_review is False
run_test('12. English regression test', test_12)

# 13. Fallback tests: invalid JSON & invalid category
def test_13():
    with patch.object(settings, 'GEMINI_API_KEY', 'test-key'):
        srv = AIService()
        mock_factory = lambda *args, **kwargs: MockAsyncClient(post_resp=make_gemini_response("{bad json"))
        with patch('httpx.AsyncClient', mock_factory):
            req = AIAnalysisRequest(description="सड़क पर गड्ढा")
            resp = drive_coro(srv.analyze_complaint(req))
            assert resp.category == "Other"
            assert resp.department is None
            assert resp.needs_human_review is True
run_test('13. Fallback test: malformed JSON', test_13)

# 14. Fallback test: missing API key
def test_14():
    with patch.object(settings, 'GEMINI_API_KEY', ''):
        srv = AIService()
        assert not srv.is_configured
        req = AIAnalysisRequest(description="सड़क पर गड्ढा")
        resp = drive_coro(srv.analyze_complaint(req))
        assert resp.needs_human_review is True
        assert resp.department is None
run_test('14. Fallback test: missing API key', test_14)

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
