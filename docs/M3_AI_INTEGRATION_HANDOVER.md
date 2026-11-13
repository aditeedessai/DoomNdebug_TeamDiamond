# AI & Intelligence Services Integration Handover (M3-09)

**Author:** Member 3 — AI & Intelligence Developer  
**Target Audience:** Member 4 — Backend, Database & Integration Lead  
**Scope:** AI Complaint Classification, Multimodal Image Understanding, Conservative Duplicate Matching, and Deterministic Priority Calculation  
**Target Release:** CivicPulse AI City Management Platform MVP

---

## 1. Ownership & Architecture Boundary

| Domain | Responsible Role | Owned Modules / Capabilities |
|---|---|---|
| **AI Intelligence Services** | **Member 3** | `backend/app/schemas/ai.py`<br>`backend/app/services/ai_service.py`<br>`backend/app/services/duplicate_service.py`<br>`backend/app/services/priority_service.py` |
| **API, DB & Orchestration** | **Member 4** | `backend/app/api/routes/complaints.py`<br>`backend/app/services/complaint_service.py`<br>`backend/app/services/storage_service.py`<br>`backend/app/database/supabase.py`<br>`backend/app/schemas/complaint.py` |

Member 3 services provide pure business intelligence, scoring, and advisory queries. Member 4 orchestrates complaint lifecycle persistence, authenticates citizens, manages database transactions, executes rollbacks, and handles official actions.

---

## 2. AI Classification Contract (`ai_service`)

### Exact Import
```python
from app.services.ai_service import ai_service
from app.schemas.ai import AIAnalysisRequest, AIAnalysisResponse
```

### Exact Invocation
```python
ai_response: AIAnalysisResponse = await ai_service.analyze_complaint(
    AIAnalysisRequest(
        description=data.description,
        latitude=data.latitude,
        longitude=data.longitude,
        image_url=data.image_url,
        language_hint=None,  # Optional: "en" or "hi"
    )
)
```

### Request Schema (`AIAnalysisRequest`)
Located in `backend/app/schemas/ai.py`:
- `description: str` *(Required)*: 1–2000 characters. Rejects empty or whitespace-only strings.
- `latitude: Optional[float] = None` *(Optional)*: Bounded to `[-90.0, 90.0]`.
- `longitude: Optional[float] = None` *(Optional)*: Bounded to `[-180.0, 180.0]`.
- `image_url: Optional[str] = None` *(Optional)*: Supabase Storage relative object path (e.g. `"complaints/<uid>/<hex>.jpg"`) or signed HTTPS URL.
- `language_hint: Optional[Literal["en", "hi"]] = None` *(Optional)*: Advisory hint from frontend portal.

### Response Schema (`AIAnalysisResponse`)
Located in `backend/app/schemas/ai.py`:
- `suggested_title: str`: 4–8 word concise summary title for `complaints.title`.
- `category: ComplaintCategory`: Canonical category string or `"Other"`.
- `issue_type: str`: Defect type (e.g. `"Pothole"`, `"Broken Streetlight"`).
- `department: Optional[DepartmentName]`: Canonical department string, or `None` if ambiguous.
- `severity: int`: Integer hazard rating from `1` through `10`.
- `summary: str`: Factual summary string for `complaints.ai_summary`.
- `recommended_action: str`: Suggested operational action for municipal field workers.
- `language: DetectedLanguage`: `"English"`, `"Hindi"`, or `"Other"`.
- `is_safety_related: bool`: True if issue impacts women's or public safety infrastructure.
- `safety_category: Optional[SafetyCategory]`: Subcategory if `is_safety_related` is True, else `None`.
- `needs_human_review: bool`: Flag indicating submission requires manual official triage.
- `review_reason: Optional[str]`: Explanation string whenever `needs_human_review` is True.

### Canonical Taxonomies
- **Categories (8):**
  1. `"Potholes, damaged roads, footpaths"`
  2. `"Broken streetlights"`
  3. `"Garbage accumulation"`
  4. `"Water leakage, drainage blockage"`
  5. `"Traffic congestion, signal faults"`
  6. `"Public park or facility damage"`
  7. `"Unsafe public infrastructure"`
  8. `"Other"` *(Forces `needs_human_review=True`)*
- **Departments (6 + `None`):**
  1. `"Public Works Department"`
  2. `"Sanitation Department"`
  3. `"Electrical Department"`
  4. `"Water & Sewerage Department"`
  5. `"Traffic & Transport Department"`
  6. `"Parks & Public Assets Department"`
  *(If unassigned or `None`, forces `needs_human_review=True`)*

### Multilingual Support (Hindi & Hinglish)
- Citizen inputs in English, Devanagari Hindi, and transliterated Hinglish are fully parsed.
- Gemini translates operational fields (`suggested_title`, `summary`, `recommended_action`) into standard English for official dashboards while preserving citizen context.
- Language hints (`language_hint`) are purely advisory. Submissions in Hindi or Hinglish are **never penalized** and do not automatically trigger manual review.

### Fallback Behavior & Exception Semantics
- `analyze_complaint()` catches all operational `Exception` subclasses (HTTP errors, timeouts, provider outages, malformed JSON, schema validation errors).
- On any operational failure or missing API key, the service immediately returns `get_fallback_response()` with `needs_human_review=True`, `category="Other"`, `department=None`, `severity=5`, and a descriptive `review_reason`.
- **Cancellation Invariant:** `asyncio.CancelledError` (which inherits from `BaseException`) is **not** swallowed. If the client disconnects or Uvicorn cancels the request, cancellation propagates cleanly.

---

## 3. Gemini Configuration & Dependencies

- **Target Model:** `gemini-3.5-flash` (`DEFAULT_MODEL = "gemini-3.5-flash"`). Note: `temperature` parameter is omitted per Google Gemini 3.5 API guidance.
- **Environment Variable:** `GEMINI_API_KEY` (loaded via `app.core.config.settings.GEMINI_API_KEY`).
  > [!IMPORTANT]
  > The local root `.env` currently does **NOT** contain `GEMINI_API_KEY`. The file `backend/.env.example` contains only a placeholder (`your-gemini-api-key`). A real key must be supplied in `.env` to enable live Gemini inference. In the absence of an API key, `ai_service` operates in safe fallback mode.
- **HTTP Client:** `httpx.AsyncClient` with a shared dynamic time budget of `8.0` seconds.
- **Required Packages:** `httpx>=0.27.0`, `pydantic>=2.6.0`, `pydantic-settings>=2.2.0` (all verified in `backend/requirements.txt`).

---

## 4. Image Understanding Contract

### Supported Formats & Size Limit
- **MIME Types:** JPEG (`image/jpeg`), PNG (`image/png`), WebP (`image/webp`). Validated via file header magic bytes (`\xff\xd8\xff`, `\x89PNG\r\n\x1a\n`, `RIFF....WEBP`).
- **File Size:** Maximum `5 MB` (`5 * 1024 * 1024` bytes), enforced via bounded streaming download.

### Input Reference
`AIAnalysisRequest.image_url` accepts either:
1. Relative object path: `"complaints/{user_id}/{filename}.{ext}"`
2. Full signed HTTPS URL: `"https://{project}.supabase.co/storage/v1/object/sign/complaint-images/..."`

> [!TIP]
> Member 4's `POST /api/v1/complaints/upload-image` endpoint returns `ImageUploadResponse` with `image_path` (e.g. `"complaints/<uid>/<hex>.jpg"`). Member 4 should pass `upload_result["image_path"]` directly as `image_url`.

### Mandatory Pre-AI Ownership Verification
Member 4 **must** verify that the citizen owns the uploaded image before calling `analyze_complaint()`. This prevents unauthorized users from using the AI service to inspect private photos uploaded by other citizens.
```python
# Exact verified method on storage_service:
if data.image_url:
    if not storage_service.validate_image_ownership(data.image_url, citizen_id_str):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: You cannot link an image uploaded by another user.",
        )
```

### SSRF Protection & Safe Retrieval
- The service whitelists only the configured `SUPABASE_URL` host, requires HTTPS on port 443, rejects embedded user credentials, disables HTTP redirects, and confines downloads to the `complaint-images` bucket.
- Service-role credentials are used only for relative object paths; signed URLs are fetched without attaching credentials.

### Shared Monotonic Timeout Budget (8.0s)
1. **Image Download:** Dynamic budget $\le 2.0$s (requires $\ge 4.5$s remaining).
2. **Gemini Inference:** Dynamic budget $\ge 2.0$s remaining.
3. **Text-Only Retry:** If multimodal inference fails, retries with text-only prompt if $\ge 3.0$s remain.
4. If image retrieval fails or times out, the service degrades gracefully to text-only classification. The citizen's written description remains authoritative for category and department.

---

## 5. Duplicate Detection Contract (`duplicate_service`)

### Exact Import
```python
from app.services.duplicate_service import duplicate_service
```

### Exact Signature
```python
async def find_duplicates(
    self,
    category: str,
    latitude: Optional[float],
    longitude: Optional[float],
    exclude_complaint_id: Optional[Union[UUID, str]] = None,
    radius_metres: float = 100.0,
    active_only: bool = True,
    candidates: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
```

### Parameters & Default Values
- `category: str`: Canonical category name (exact match required; non-canonical returns `[]`).
- `latitude`, `longitude`: Target coordinates (-90.0 to 90.0, -180.0 to 180.0). Missing or non-numeric returns `[]`.
- `exclude_complaint_id: Optional[Union[UUID, str]] = None`: Excludes current complaint from matching (case-insensitive string or UUID comparison).
- `radius_metres: float = 100.0`: Spatial search radius using Haversine formula ($R = 6,371,000$ m).
- `active_only: bool = True`: When True, restricts search to active statuses (`"Submitted"`, `"Under Review"`, `"Assigned"`, `"In Progress"`, `"Needs More Information"`). Excludes `"Resolved"` and `"Rejected"`.
- `candidates: Optional[List[Dict[str, Any]]] = None`: When provided (even `[]`), evaluates the candidate list in-memory without querying Supabase. When `None`, performs a read-only PostgREST GET query against `complaints`.

### Output Structure (Zero PII, Sorted by Distance Ascending)
```python
[
    {
        "complaint_id": "c1111111-1111-1111-1111-111111111111",
        "title": "Deep pothole near junction",
        "category": "Potholes, damaged roads, footpaths",
        "issue_type": "Pothole",
        "status": "Submitted",
        "distance_meters": 28.4,
        "report_count": 2,
        "created_at": "2026-11-13T10:00:00Z"
    }
]
```

### Invariants
- **Read-Only:** Uses only HTTP `GET`. Never performs `POST`, `PATCH`, `PUT`, or `DELETE`.
- **No Auto-Merge:** Never merges records, deletes complaints, or alters database state.
- **Privacy:** Strips `citizen_id`, `phone`, citizen names, and detailed descriptions.

---

## 6. Priority Calculation Contract (`priority_service`)

### Exact Import
```python
from app.services.priority_service import priority_service
```

### Exact Signatures
```python
def calculate_priority(
    self,
    severity: int,
    report_count: int = 1,
    overdue_bonus: int = 0
) -> str

def calculate_priority_score(
    self,
    severity: int,
    report_count: int = 1,
    overdue_bonus: int = 0
) -> int
```

### Formula & Thresholds
$$\text{Priority Score} = (\text{severity} \times 10) + ((\text{report\_count} - 1) \times 5) + \text{overdue\_bonus}$$

- **Score $\ge 80$:** `"Critical"`
- **Score $60$ to $79$:** `"High"`
- **Score $35$ to $59$:** `"Medium"`
- **Score $0$ to $34$:** `"Low"`

### Input Validation
- `severity`: integer `1` through `10`.
- `report_count`: integer $\ge 1$.
- `overdue_bonus`: integer $\ge 0$ (defaults to `0`).
- Community bonus is **uncapped** per the agreed formula.
- Rejects booleans explicitly (`True`/`False`), floats, strings, `None`, `NaN`, and `inf` with `ValueError`.
- **Pure Function Invariant:** `priority_service` does **NOT** inspect timestamps or calculate SLA deadlines. Member 4 evaluates municipal overdue policies and passes `overdue_bonus` as an integer.

---

## 7. Recommended End-to-End Complaint Ingestion Sequence

The following pseudocode demonstrates the recommended flow inside `complaint_service.create_complaint`:

```python
# Step 1: Enforce image ownership before calling any external or AI service
if data.image_url:
    if not storage_service.validate_image_ownership(data.image_url, citizen_id_str):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: You cannot link an image uploaded by another user.",
        )

# Step 2: Analyze complaint with AI (8.0s deadline, safe fallback guaranteed)
ai_result = await ai_service.analyze_complaint(
    AIAnalysisRequest(
        description=data.description,
        latitude=data.latitude,
        longitude=data.longitude,
        image_url=data.image_url,
    )
)

# Step 3: Calculate deterministic priority
calculated_priority = priority_service.calculate_priority(
    severity=ai_result.severity,
    report_count=1,
    overdue_bonus=0,
)

# Step 4: Map AI department string to database department_id UUID
resolved_dept_id = None
if ai_result.department:
    dept_rows = await supabase_service.rest_query(
        "departments",
        method="GET",
        params={"name": f"eq.{ai_result.department}", "select": "id"}
    )
    if dept_rows and isinstance(dept_rows, list) and len(dept_rows) > 0:
        resolved_dept_id = dept_rows[0]["id"]

# Step 5: Map safety fields (citizen safety intent is never downgraded)
effective_safety = bool(data.safety_related or ai_result.is_safety_related)
effective_safety_category = data.safety_category or (
    ai_result.safety_category if effective_safety else None
)

# Step 6: Construct database payload
payload = {
    "citizen_id": citizen_id_str,
    "title": ai_result.suggested_title or data.title.strip(),
    "description": data.description.strip(),
    "latitude": data.latitude,
    "longitude": data.longitude,
    "category": ai_result.category,
    "issue_type": ai_result.issue_type,
    "department_id": resolved_dept_id,
    "image_url": data.image_url,
    "severity": ai_result.severity,
    "priority": calculated_priority,
    "ai_summary": ai_result.summary,
    "safety_related": effective_safety,
    "safety_category": effective_safety_category,
    "status": "Submitted",
    "report_count": 1,
}

# Step 7: Persist complaint to database (Member 4 handles insert & history)
created = await supabase_service.rest_query("complaints", method="POST", json_data=payload)
# ... handle compensating rollback and complaint_updates history insert ...

# Step 8: Advisory duplicate detection (does not merge or mutate records)
possible_duplicates = await duplicate_service.find_duplicates(
    category=ai_result.category,
    latitude=data.latitude,
    longitude=data.longitude,
    exclude_complaint_id=created[0]["id"],
    radius_metres=100.0,
)
```

---

## 8. Safety Field Mapping Reference

| Source Field | Schema / Location | Type | Notes |
|---|---|---|---|
| `ai_result.is_safety_related` | `AIAnalysisResponse` | `bool` | Note the `is_` prefix |
| `data.safety_related` | `ComplaintCreate` | `bool` | Citizen form flag |
| `payload["safety_related"]` | `complaints` table | `BOOLEAN` | Database column |
| `ai_result.safety_category` | `AIAnalysisResponse` | `Optional[str]` | Detected hazard category |
| `data.safety_category` | `ComplaintCreate` | `Optional[str]` | Citizen selected category |
| `payload["safety_category"]` | `complaints` table | `TEXT` | Database column |

### Approved Mapping Rule
```python
effective_safety = bool(data.safety_related or ai_result.is_safety_related)
effective_category = data.safety_category or (ai_result.safety_category if effective_safety else None)
```
- A citizen's explicit safety report is **never downgraded** by the AI.
- If the citizen did not mark safety, but Gemini identifies a public/women's safety concern, the complaint is upgraded.

---

## 9. Official Duplicate Linking & Priority Recalculation (`M4-04`)

When an authorized municipal official reviews advisory duplicates and confirms Complaint B is a duplicate of Master Complaint A:

```python
# 1. Fetch current master record
master_rows = await supabase_service.rest_query(
    "complaints", method="GET", params={"id": f"eq.{master_id}"}
)
master = master_rows[0]

# 2. Increment community report count
new_report_count = int(master.get("report_count", 1)) + 1

# 3. Recalculate priority using existing master severity and new report count
new_priority = priority_service.calculate_priority(
    severity=int(master["severity"]),
    report_count=new_report_count,
    overdue_bonus=0,  # Or pass overdue bonus if master is overdue
)

# 4. Update master complaint record
await supabase_service.rest_query(
    "complaints",
    method="PATCH",
    params={"id": f"eq.{master_id}"},
    json_data={
        "report_count": new_report_count,
        "priority": new_priority,
    }
)

# 5. Link child complaint to master incident
await supabase_service.rest_query(
    "complaints",
    method="PATCH",
    params={"id": f"eq.{child_id}"},
    json_data={
        "master_incident_id": master_id,
        "status": "Under Review",
    }
)
```

---

## 10. Error Handling & Security Responsibility Matrix

| Concern | Member 3 Responsibility | Member 4 Responsibility |
|---|---|---|
| **AI Inference Outages** | Catches `Exception`, manages 8.0s timeout, returns fallback response. | No custom try/except needed for AI; processes `needs_human_review`. |
| **Task Cancellation** | Lets `asyncio.CancelledError` propagate cleanly. | Handles standard Uvicorn/FastAPI client disconnection semantics. |
| **Image Ownership Security** | None (validates paths and hosts, not user sessions). | **Must** call `storage_service.validate_image_ownership` before AI analysis. |
| **Image Content Security** | Rejects non-Supabase hosts, non-443, redirects, >5MB, invalid magic bytes. | Handles image upload staging in Supabase Storage. |
| **Department Resolution** | Returns canonical department string (or `None`). | Queries `departments` table for matching UUID `department_id`. |
| **Duplicate Matching** | Calculates Haversine distance, filters category/status, returns sanitized list. | Displays advisory duplicates to officials; manages manual linking. |
| **Priority Calculation** | Pure function mapping severity + count + overdue to Priority string. | Supplies integer inputs from database; manages overdue policy timing. |
| **Database Consistency** | Strictly read-only; no database writes. | Manages database inserts, status history entries, and rollback cleanup. |

---

## 11. Known Limitations & Configuration Checklist

1. **`GEMINI_API_KEY` Presence:**
   - The root `.env` currently omits `GEMINI_API_KEY`.
   - Before live AI testing, Member 4 must ensure `GEMINI_API_KEY="<actual_key>"` is set in `.env`.
   - Until configured, the AI service functions entirely in deterministic fallback mode.
2. **Mocked Unit Tests vs. Live API:**
   - Member 3 unit tests (`test_m3_02.py` through `test_m3_08.py`) use mocked HTTP clients to prevent external network coupling during build. Live connectivity to Google's API endpoint has not been verified in the local offline sandbox.
3. **Department Mapping:**
   - Database seed data contains 6 departments matching Member 3's taxonomy. Member 4 must handle mapping `"Other"` or unassigned complaints (`department=None`) by leaving `department_id=NULL` (triggering unassigned triage).
4. **Overdue Calculation Policy:**
   - `priority_service` does not inspect timestamps. When implementing overdue policies in M4-04, Member 4 should evaluate complaint age (e.g. `now - created_at > 48h`) and supply an integer `overdue_bonus`.

---

## 12. Quick Integration Checklist for Member 4

- [ ] Add `GEMINI_API_KEY="<key>"` to root `.env`.
- [ ] Import `ai_service` and `AIAnalysisRequest` in `complaint_service.py`.
- [ ] Validate image ownership via `storage_service.validate_image_ownership` before calling `ai_service`.
- [ ] Pass `data.image_url` (relative path) to `AIAnalysisRequest`.
- [ ] Call `ai_service.analyze_complaint(request)`.
- [ ] Import `priority_service` and call `calculate_priority(severity=ai_result.severity, report_count=1)`.
- [ ] Resolve `ai_result.department` to `department_id` UUID via `departments` table lookup.
- [ ] Map safety fields using `effective_safety = bool(data.safety_related or ai_result.is_safety_related)`.
- [ ] Import `duplicate_service` and call `find_duplicates(...)` after complaint creation.
- [ ] In M4-04 duplicate linking, increment `master.report_count` and recalculate priority.
