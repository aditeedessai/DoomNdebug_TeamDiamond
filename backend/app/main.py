"""FastAPI Application entrypoint for AI City Management Platform.

Task: M4-10 Seed Data & API Documentation (Step 3: OpenAPI & Swagger Documentation Enhancement)
Role: Member 4 (Backend, Database & Integration Lead)
"""
from typing import Any, Dict, List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.api.routes import api_router

# ==============================================================================
# API METADATA & DOCUMENTATION
# ==============================================================================
API_TITLE = "AI City Management Platform API"
API_VERSION = "1.0.0"

API_DESCRIPTION = """
# AI City Management Platform API

Comprehensive backend service providing collaborative municipal governance, real-time civic incident management, citizen engagement, spatial visualization, and field worker dispatch.

Built with **FastAPI**, **Supabase PostgreSQL**, and **Google Gemini AI**.

---

## 1. Platform Roles & Authorization Matrix

The platform enforces strict role-based and department-scoped access control across four authenticated roles:

* **Citizen (`citizen`)**:
  * Submit civic complaints and women's infrastructure safety reports with GPS coordinates and optional photographic evidence.
  * Track status progression and chronological timeline history for own submitted complaints (`/api/v1/complaints/my`) and own safety reports (`/api/v1/safety-reports/mine`).
  * Review ongoing and planned municipal projects and submit community feedback.
  * View sanitized public map markers and privacy-preserving aggregated safety zones ($k \\ge 3$).
* **Municipal Official (`official`)**:
  * Department-scoped complaint triage, investigation status updates, severity rating, and priority assignment.
  * Department assignment for unassigned complaints, inter-departmental routing (city-wide officials only), and duplicate incident linking.
  * Dispatch rapid response field crews and track municipal worker task assignments.
  * Manage municipal capital projects, publish public project updates, and triage citizen feedback.
  * Access operational dashboard metrics, resolution rates, and department performance statistics.
  * *Note*: Ordinary officials cannot access the restricted women's safety reports register or view granular safety incident data.
* **Designated Safety Officer (`official` with `is_safety_officer = true`)**:
  * Authorized access to the restricted Women's Infrastructure Safety Register (`/api/v1/safety-reports`).
  * Review and investigate granular safety reports across all municipal departments (dark corridors, desolate transit stops, broken streetlighting).
  * Update safety investigation statuses and dispatch specialized lighting, electrical, and transit safety remediation work orders.
* **Field Worker (`worker`)**:
  * Review assigned municipal repair and maintenance work orders.
  * Update assignment status (`Assigned` $\\to$ `In Progress` $\\to$ `Completed`) and log progress remarks.
  * Access restricted strictly to own assigned tasks and linked worker profile. Workers cannot access general complaint registers, safety reports, or map data.

---

## 2. Authentication & JWT Bearer Token Usage

The API uses stateless JSON Web Token (JWT) authentication issued by **Supabase Auth**.

### Interactive Swagger UI Authorize Workflow:
1. Click the green **Authorize** button at the top right of this Swagger UI documentation page.
2. In the `bearerAuth` dialog, paste only your **raw Supabase JWT access token** into the **Value** input field.
   * Do **NOT** type `Bearer `; Swagger UI automatically formats the HTTP header as `Authorization: Bearer <token>`.
3. Click **Authorize**, then click **Close**.
4. All subsequent interactive requests to protected endpoints will automatically include the required `Authorization: Bearer <token>` header.

### Error Semantics:
* **`HTTP 401 Unauthorized`**: Returned when the `Authorization` header is missing, malformed, or contains an expired or invalid JWT token.
* **`HTTP 403 Forbidden`**: Returned when an authenticated user attempts to access an endpoint outside their role permissions (e.g. citizen accessing official registers) or when a department official attempts to modify a complaint outside their assigned department.

---

## 3. Department-Level Scoping & Boundaries

Municipal operations are partitioned across six functional departments:
1. **Public Works Department (`PWD`)**: Road maintenance, potholes, bridges, sidewalks, and civil structures.
2. **Sanitation Department**: Waste management, public bin clearance, and street cleanliness.
3. **Electrical Department**: Street lighting, traffic signal power, and electrical infrastructure.
4. **Water & Sewerage Department**: Drinking water supply pipelines, sewer line drainage, and manholes.
5. **Traffic & Transport Department**: Traffic flow management, public bus stops, and road signage.
6. **Parks & Public Assets Department**: Public gardens, trees, municipal buildings, and community centers.

### Department Assignment & Transfer Rules:
* **Initial Assignment**: When a complaint is newly submitted without a department, a department official can assign it to their own department, while a general official (with `department_id = null`) can assign it to any valid department.
* **Department-Scoped Confinement**: Officials assigned to a specific department can view, update, triage, and dispatch workers only for complaints belonging to their assigned department. Cross-department access attempts are rejected with `HTTP 403 Forbidden`.
* **No Cross-Department Transfers by Department Officials**: An official assigned to Department A cannot reassign or transfer an existing complaint to Department B.
* **City-Wide Administrative Oversight**: Only general officials (`department_id = null`) possess unconstrained authority to reassign or transfer existing complaints across departmental boundaries.

---

## 4. Women's Infrastructure Safety & Privacy Safeguards

To protect vulnerable citizens and comply with municipal privacy protocols:
* **Citizen Ownership**: Citizens can submit safety reports and review the full details and investigation timeline of their own submitted reports via `/api/v1/safety-reports/mine` and `/api/v1/safety-reports/{id}`. Citizens cannot view other citizens' safety reports.
* **Restricted Safety Register**: The comprehensive city-wide safety reports register (`GET /api/v1/safety-reports`) and investigation updates (`PATCH /api/v1/safety-reports/{id}`) are restricted strictly to designated safety officers (`role = 'official'` and `is_safety_officer = true`). Ordinary officials and workers are strictly denied access (`HTTP 403 Forbidden`).
* **General Complaint & Map Exclusion**: Safety reports are excluded from the general complaints register and general map marker endpoints for citizens and ordinary officials.
* **Privacy-Preserving Aggregated Safety Zones ($k \\ge 3$)**: Public map users and ordinary officials view safety data only as spatially aggregated cluster zones (`/api/v1/map/safety-zones`). Reports are discretized into 0.01° grid cells (~1.1 km); grid cells with fewer than 3 reports ($k < 3$) are suppressed entirely to prevent individual report identification.

---

## 5. API Versioning & Documentation URLs

* **Base Route Prefix**: `/api/v1`
* **Interactive Swagger UI**: [`/docs`](/docs)
* **ReDoc Specification**: [`/redoc`](/redoc)
* **OpenAPI 3.1 JSON Specification**: [`/api/v1/openapi.json`](/api/v1/openapi.json)
"""

# ==============================================================================
# OPENAPI TAGS METADATA (NINE CANONICAL DOMAINS)
# ==============================================================================
TAGS_METADATA: List[Dict[str, Any]] = [
    {
        "name": "Authentication",
        "description": (
            "User registration, JWT login, and authenticated user profile retrieval via Supabase Auth. "
            "Registration and login are public; `/me` requires an authenticated citizen, official, or worker token."
        ),
    },
    {
        "name": "Complaints",
        "description": (
            "Civic complaint lifecycle management including citizen submission, photographic upload, "
            "department assignment, priority assessment, duplicate incident linking, and official status transitions. "
            "Citizens access their own submissions; department officials manage complaints within their department; "
            "general officials manage city-wide complaints and cross-department routing."
        ),
    },
    {
        "name": "Projects",
        "description": (
            "Municipal infrastructure projects registry, progress milestone tracking, and publication boundaries. "
            "Officials create and update capital projects; citizens view published projects."
        ),
    },
    {
        "name": "Feedback",
        "description": (
            "Citizen feedback on ongoing and planned municipal infrastructure projects, with official triage "
            "and one-click conversion into tracked civic complaints."
        ),
    },
    {
        "name": "Map and Traffic",
        "description": (
            "Geospatial data layers for public civic complaints, municipal projects, traffic congestion hotspots, "
            "and privacy-preserving aggregated safety zones ($k \\ge 3$). Workers are restricted from general map data."
        ),
    },
    {
        "name": "Safety Reports",
        "description": (
            "Women's infrastructure safety reports (dark corridors, desolate transit stops, harassment hazards). "
            "Citizens submit reports and track their own submissions (`/mine`). The comprehensive safety register, "
            "granular incident details, and status updates are restricted strictly to designated safety officers "
            "(`role = official` AND `is_safety_officer = true`). Ordinary officials and workers are denied access."
        ),
    },
    {
        "name": "Dashboard",
        "description": (
            "Role-discriminated municipal metrics, department performance statistics, resolution rates, priority breakdowns, "
            "and safety incident summaries. Citizens receive personal metrics; officials receive department analytics; "
            "safety officers access safety KPIs."
        ),
    },
    {
        "name": "Workers",
        "description": (
            "Municipal field teams and rapid response crew registry, department scoping, and field availability status "
            "(`Available`, `Busy`, `Unavailable`). Accessible to municipal officials and authenticated workers."
        ),
    },
    {
        "name": "Assignments",
        "description": (
            "Field task dispatch linking workers to civic complaints or traffic hotspots with strict single-target XOR "
            "enforcement. Dispatched and managed by officials; progress updated by assigned workers. Citizens denied access."
        ),
    },
    {
        "name": "Health",
        "description": "System health and operational readiness probes for service orchestration and load balancers.",
    },
]


def create_application() -> FastAPI:
    """Application factory for FastAPI service with enhanced OpenAPI metadata."""
    application = FastAPI(
        title=API_TITLE,
        version=API_VERSION,
        description=API_DESCRIPTION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        openapi_tags=TAGS_METADATA,
    )

    # Configure CORS middleware
    # Strip any trailing slashes from origins for precise match
    allowed_origins = [str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS]

    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Root health check endpoint
    @application.get("/health", tags=["Health"], summary="Root Health Check")
    async def root_health():
        """Root-level operational health probe confirming service availability."""
        return {
            "status": "ok",
            "version": API_VERSION,
        }

    # Mount versioned modular API router (/api/v1)
    application.include_router(api_router, prefix=settings.API_V1_STR)

    # --------------------------------------------------------------------------
    # Custom OpenAPI Schema Configuration
    # - Injects standard HTTP Bearer JWT security scheme for Swagger UI Authorize
    # - Standardizes operation tags to the nine canonical domain names
    # - Marks public endpoints explicitly with no security requirement
    # --------------------------------------------------------------------------
    def custom_openapi() -> Dict[str, Any]:
        if application.openapi_schema:
            return application.openapi_schema

        openapi_schema = get_openapi(
            title=application.title,
            version=application.version,
            description=application.description,
            routes=application.routes,
            tags=application.openapi_tags,
        )

        # 1. Define HTTP Bearer JWT security scheme
        # Declares bearerAuth as the sole security scheme to prevent confusing duplicate entries in Swagger UI
        components = openapi_schema.setdefault("components", {})
        security_schemes = components.setdefault("securitySchemes", {})
        security_schemes.clear()
        security_schemes["bearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "Enter your raw Supabase Auth JWT access token. "
                "Do NOT include the 'Bearer ' prefix; Swagger UI automatically prepends 'Bearer '."
            ),
        }

        # 2. Tag mapping from router prefixes to canonical domain names
        tag_normalization = {
            "auth": "Authentication",
            "complaints": "Complaints",
            "projects": "Projects",
            "feedback": "Feedback",
            "map": "Map and Traffic",
            "safety-reports": "Safety Reports",
            "dashboard": "Dashboard",
            "workers": "Workers",
            "assignments": "Assignments",
            "health": "Health",
        }

        # Public endpoints that do not require authentication
        public_endpoints = {
            "/health",
            f"{settings.API_V1_STR}/health",
            f"{settings.API_V1_STR}/auth/register",
            f"{settings.API_V1_STR}/auth/login",
        }

        for path, methods in openapi_schema.get("paths", {}).items():
            for method, operation in methods.items():
                # Normalize tags to match TAGS_METADATA
                if "tags" in operation:
                    operation["tags"] = [tag_normalization.get(t, t) for t in operation["tags"]]

                # Set security requirements: public endpoints get empty security; protected get bearerAuth
                if path in public_endpoints:
                    operation["security"] = []
                else:
                    operation["security"] = [{"bearerAuth": []}]

        application.openapi_schema = openapi_schema
        return application.openapi_schema

    application.openapi = custom_openapi

    return application


app = create_application()
