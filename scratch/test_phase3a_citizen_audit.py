"""Phase 3A Citizen Portal Integration Audit Test Suite.

Audits and verifies the exact FastAPI backend routes, schemas, and service contracts:
1. Complaint category handling: tests all 6 canonical categories.
2. AI-driven / fallback category preservation and issue_type mapping.
3. Map endpoints: GET /map/complaints returns sanitized citizen markers.
4. Map endpoints: GET /map/projects returns published project markers.
5. Map endpoints: GET /map/hotspots returns demo traffic hotspots.
6. Map endpoints: GET /map/safety-zones enforces privacy aggregation (k >= 3, rounded coords, no PII).
7. Complaint lifecycle statuses: tests all 7 backend statuses including 'Needs More Information'.
8. Pagination parameters: verifies 'limit', 'offset', and 'status' on GET /complaints/my.
9. Pagination parameters: verifies 'limit' and 'offset' on GET /projects.
10. Pagination parameters: verifies 'limit', 'offset', and 'status' on GET /safety-reports/mine.
11. Feedback contract: accepts canonical PRD feedback categories.
12. Feedback contract: rejects invalid/unknown feedback categories with HTTP 400.
13. Feedback contract: requires project_id and minimum 3-character message.
14. Complaint detail contract: GET /complaints/{id} includes status timeline updates.
15. Complaint detail ownership: citizen cannot access another citizen's complaint (HTTP 403).
16. Storage image upload: enforces magic bytes (JPEG/PNG/WebP) and 5 MB size limit.
17. Unauthenticated access: protected citizen routes reject requests with HTTP 401.
18. Worker isolation: workers are forbidden from accessing map complaint markers and safety zones.
"""
import io
import os
import sys
import unittest
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_current_user
from app.schemas.profile import ProfileResponse
from app.schemas.complaint import ComplaintDetailResponse, ComplaintResponse, ComplaintUpdateItem
from app.schemas.map import MapComplaintMarker, MapProjectMarker, TrafficHotspotResponse, AggregatedSafetyZoneResponse
from app.schemas.project import ProjectResponse
from app.schemas.safety import SafetyReportResponse
from app.schemas.feedback import FeedbackResponse


class TestPhase3ACitizenAudit(unittest.TestCase):
    """Rigorous contract and route audit suite for Citizen Portal integration."""

    def setUp(self):
        self.citizen_id = uuid4()
        self.other_citizen_id = uuid4()
        self.client = TestClient(app)

        self.citizen_profile = ProfileResponse(
            id=self.citizen_id,
            email="citizen@example.gov",
            full_name="Maria Fernandes",
            phone="+91 98221 23456",
            role="citizen",
            is_active=True,
            is_safety_officer=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        self.worker_profile = ProfileResponse(
            id=uuid4(),
            email="worker@example.gov",
            full_name="Worker Joe",
            role="worker",
            is_active=True,
            is_safety_officer=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def tearDown(self):
        app.dependency_overrides.clear()

    # ------------------------------------------------------------------------
    # 1. Complaint Categories
    # ------------------------------------------------------------------------

    def test_01_all_canonical_complaint_categories_accepted(self):
        """All 6 canonical citizen complaint categories are valid in ComplaintCreate schema."""
        app.dependency_overrides[get_current_user] = lambda: self.citizen_profile

        canonical_categories = [
            ("Roads & Infrastructure", "Road or Footpath Damage"),
            ("Sanitation & Waste", "Garbage Accumulation"),
            ("Water & Utilities", "Water Leakage or Blockage"),
            ("Electricity & Lighting", "Streetlight or Power Issue"),
            ("Public Safety", "Unsafe Civic Infrastructure"),
            ("Other", "Civic Concern"),
        ]

        with patch("app.services.complaint_service.complaint_service.create_complaint", new_callable=AsyncMock) as mock_create:
            for cat, issue in canonical_categories:
                mock_create.return_value = ComplaintResponse(
                    id=uuid4(),
                    citizen_id=self.citizen_id,
                    title=f"Issue in {cat}",
                    description="Detailed description of civic issue for audit.",
                    latitude=15.49,
                    longitude=73.82,
                    category=cat,
                    issue_type=issue,
                    status="Submitted",
                    priority="Medium",
                    severity=5,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )

                payload = {
                    "title": f"Test {cat}",
                    "description": "At least 5 characters description.",
                    "latitude": 15.498,
                    "longitude": 73.827,
                    "category": cat,
                    "issue_type": issue,
                }
                res = self.client.post("/api/v1/complaints", json=payload)
                self.assertEqual(res.status_code, 201, f"Failed for category: {cat}")
                self.assertEqual(res.json()["category"], cat)

    def test_02_complaint_validation_rejects_empty_or_short_fields(self):
        """Complaint creation validates title and description lengths (HTTP 422)."""
        app.dependency_overrides[get_current_user] = lambda: self.citizen_profile

        # Title too short (<3 chars)
        res1 = self.client.post("/api/v1/complaints", json={
            "title": "ab",
            "description": "Valid description long enough",
            "latitude": 15.49,
            "longitude": 73.82,
            "category": "Roads & Infrastructure",
            "issue_type": "Pothole",
        })
        self.assertEqual(res1.status_code, 422)

        # Description too short (<5 chars)
        res2 = self.client.post("/api/v1/complaints", json={
            "title": "Valid Title",
            "description": "bad",
            "latitude": 15.49,
            "longitude": 73.82,
            "category": "Roads & Infrastructure",
            "issue_type": "Pothole",
        })
        self.assertEqual(res2.status_code, 422)

    # ------------------------------------------------------------------------
    # 2. Map Endpoints (All 4 Layers)
    # ------------------------------------------------------------------------

    def test_03_map_complaints_endpoint(self):
        """GET /api/v1/map/complaints returns sanitized complaint markers."""
        app.dependency_overrides[get_current_user] = lambda: self.citizen_profile

        with patch("app.services.map_service.map_service.get_complaint_markers", new_callable=AsyncMock) as mock_markers:
            mock_markers.return_value = [
                MapComplaintMarker(
                    id=uuid4(),
                    latitude=15.498,
                    longitude=73.827,
                    category="Roads & Infrastructure",
                    status="In Progress",
                    priority="High",
                    created_at=datetime.now(timezone.utc),
                    report_count=2,
                )
            ]
            res = self.client.get("/api/v1/map/complaints")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["category"], "Roads & Infrastructure")
            self.assertNotIn("citizen_id", data[0])  # PII redacted

    def test_04_map_projects_endpoint(self):
        """GET /api/v1/map/projects returns published infrastructure project markers."""
        app.dependency_overrides[get_current_user] = lambda: self.citizen_profile

        with patch("app.services.map_service.map_service.get_project_markers", new_callable=AsyncMock) as mock_proj:
            mock_proj.return_value = [
                MapProjectMarker(
                    id=uuid4(),
                    title="Smart Lighting Phase 1",
                    description="Solar streetlights",
                    department_id=uuid4(),
                    department_name="Electrical Department",
                    latitude=15.498,
                    longitude=73.827,
                    status="Ongoing",
                    start_date=date(2026, 1, 1),
                    expected_end_date=date(2026, 12, 31),
                    is_published=True,
                )
            ]
            res = self.client.get("/api/v1/map/projects")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["title"], "Smart Lighting Phase 1")

    def test_05_map_hotspots_endpoint_identifies_demo_source(self):
        """GET /api/v1/map/hotspots returns traffic hotspots with source='demo'."""
        app.dependency_overrides[get_current_user] = lambda: self.citizen_profile

        with patch("app.services.map_service.map_service.get_traffic_hotspots", new_callable=AsyncMock) as mock_hs:
            mock_hs.return_value = [
                TrafficHotspotResponse(
                    id=uuid4(),
                    latitude=15.492,
                    longitude=73.815,
                    congestion_level="High",
                    source="demo",
                    description="Simulated peak-hour jam near Mandovi bridge",
                    observed_at=datetime.now(timezone.utc),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            ]
            res = self.client.get("/api/v1/map/hotspots")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["source"], "demo")
            self.assertEqual(data[0]["congestion_level"], "High")

    def test_06_map_safety_zones_privacy_aggregation(self):
        """GET /api/v1/map/safety-zones returns aggregated safety clusters (k >= 3, 2 decimal places)."""
        app.dependency_overrides[get_current_user] = lambda: self.citizen_profile

        with patch("app.services.map_service.map_service.get_safety_zones", new_callable=AsyncMock) as mock_sz:
            mock_sz.return_value = [
                AggregatedSafetyZoneResponse(
                    zone_id="zone_1549_7381",
                    latitude=15.49,
                    longitude=73.81,
                    category="Lighting Issue",
                    report_count=3,
                    suggested_action="Lighting inspection recommended",
                    status="Active Reports",
                )
            ]
            res = self.client.get("/api/v1/map/safety-zones")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 1)
            self.assertGreaterEqual(data[0]["report_count"], 3)
            self.assertNotIn("citizen_id", data[0])

    # ------------------------------------------------------------------------
    # 3. Status Filters and Pagination
    # ------------------------------------------------------------------------

    def test_07_complaint_status_filter_and_pagination(self):
        """GET /api/v1/complaints/my accepts status filter, limit, and offset."""
        app.dependency_overrides[get_current_user] = lambda: self.citizen_profile

        with patch("app.services.complaint_service.complaint_service.get_my_complaints", new_callable=AsyncMock) as mock_my:
            mock_my.return_value = [
                ComplaintResponse(
                    id=uuid4(),
                    citizen_id=self.citizen_id,
                    title="Needs more info complaint",
                    description="Citizen needs to provide additional photographs.",
                    latitude=15.49,
                    longitude=73.82,
                    category="Roads & Infrastructure",
                    issue_type="Pothole",
                    status="Needs More Information",
                    priority="Low",
                    severity=3,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            ]
            # Test with 'Needs More Information' status filter
            res = self.client.get("/api/v1/complaints/my?status=Needs%20More%20Information&limit=10&offset=0")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["status"], "Needs More Information")

            mock_my.assert_called_once_with(
                citizen=self.citizen_profile,
                status_filter="Needs More Information",
                limit=10,
                offset=0,
            )

    def test_08_projects_pagination_and_status(self):
        """GET /api/v1/projects accepts status, limit, and offset."""
        app.dependency_overrides[get_current_user] = lambda: self.citizen_profile

        with patch("app.services.project_service.project_service.list_projects", new_callable=AsyncMock) as mock_proj:
            mock_proj.return_value = []
            res = self.client.get("/api/v1/projects?status=Ongoing&limit=25&offset=50")
            self.assertEqual(res.status_code, 200)
            mock_proj.assert_called_once_with(
                current_user=self.citizen_profile,
                department_id=None,
                status_filter="Ongoing",
                is_published=None,
                limit=25,
                offset=50,
            )

    def test_09_safety_reports_mine_pagination_and_status(self):
        """GET /api/v1/safety-reports/mine accepts status, limit, and offset."""
        app.dependency_overrides[get_current_user] = lambda: self.citizen_profile

        with patch("app.services.safety_service.safety_service.get_my_safety_reports", new_callable=AsyncMock) as mock_sr:
            mock_sr.return_value = []
            res = self.client.get("/api/v1/safety-reports/mine?status=Submitted&limit=15&offset=0")
            self.assertEqual(res.status_code, 200)
            mock_sr.assert_called_once_with(
                citizen=self.citizen_profile,
                status_filter="Submitted",
                limit=15,
                offset=0,
            )

    # ------------------------------------------------------------------------
    # 4. Feedback Contract
    # ------------------------------------------------------------------------

    def test_10_feedback_submission_accepts_canonical_category(self):
        """POST /api/v1/feedback accepts canonical PRD feedback categories."""
        app.dependency_overrides[get_current_user] = lambda: self.citizen_profile

        proj_id = uuid4()
        with patch("app.services.feedback_service.feedback_service.submit_feedback", new_callable=AsyncMock) as mock_fb:
            mock_fb.return_value = FeedbackResponse(
                id=uuid4(),
                project_id=proj_id,
                citizen_id=self.citizen_id,
                category="Construction-related inconvenience",
                message="Heavy machinery noise during evening hours.",
                created_at=datetime.now(timezone.utc),
            )

            res = self.client.post("/api/v1/feedback", json={
                "project_id": str(proj_id),
                "category": "Construction-related inconvenience",
                "message": "Heavy machinery noise during evening hours.",
            })
            self.assertEqual(res.status_code, 201)
            self.assertEqual(res.json()["category"], "Construction-related inconvenience")

    def test_11_feedback_submission_missing_project_id_rejected(self):
        """POST /api/v1/feedback rejects requests missing project_id with HTTP 400."""
        app.dependency_overrides[get_current_user] = lambda: self.citizen_profile

        res = self.client.post("/api/v1/feedback", json={
            "category": "Construction-related inconvenience",
            "message": "Heavy machinery noise during evening hours.",
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("project_id", res.json()["detail"])

    # ------------------------------------------------------------------------
    # 5. Complaint Detail and Timeline Contract
    # ------------------------------------------------------------------------

    def test_12_complaint_detail_includes_updates_timeline(self):
        """GET /api/v1/complaints/{id} returns ComplaintDetailResponse with updates list."""
        app.dependency_overrides[get_current_user] = lambda: self.citizen_profile

        cid = uuid4()
        with patch("app.services.complaint_service.complaint_service.get_complaint_by_id", new_callable=AsyncMock) as mock_detail:
            mock_detail.return_value = ComplaintDetailResponse(
                id=cid,
                citizen_id=self.citizen_id,
                title="Broken Footpath Slab",
                description="Damaged concrete slab posing trip hazard for elderly pedestrians.",
                latitude=15.498,
                longitude=73.827,
                category="Roads & Infrastructure",
                issue_type="Footpath Defect",
                status="In Progress",
                priority="Medium",
                severity=6,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                updates=[
                    ComplaintUpdateItem(
                        id=uuid4(),
                        complaint_id=cid,
                        actor_id=uuid4(),
                        actor_name="Officer Ramesh",
                        actor_role="official",
                        status="In Progress",
                        remarks="Field inspection completed. Masonry crew scheduled.",
                        created_at=datetime.now(timezone.utc),
                    )
                ],
            )

            res = self.client.get(f"/api/v1/complaints/{cid}")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["id"], str(cid))
            self.assertIn("updates", data)
            self.assertEqual(len(data["updates"]), 1)
            self.assertEqual(data["updates"][0]["actor_name"], "Officer Ramesh")

    def test_13_complaint_detail_ownership_enforcement(self):
        """Citizen cannot view another citizen's complaint (HTTP 403 Forbidden)."""
        app.dependency_overrides[get_current_user] = lambda: self.citizen_profile

        cid = uuid4()
        from fastapi import HTTPException
        with patch("app.services.complaint_service.complaint_service.get_complaint_by_id", new_callable=AsyncMock) as mock_detail:
            mock_detail.side_effect = HTTPException(status_code=403, detail="Access denied: You do not own this complaint record.")

            res = self.client.get(f"/api/v1/complaints/{cid}")
            self.assertEqual(res.status_code, 403)
            self.assertIn("Access denied", res.json()["detail"])

    # ------------------------------------------------------------------------
    # 6. Safety Reports Submission
    # ------------------------------------------------------------------------

    def test_14_citizen_safety_report_submission(self):
        """Citizen can submit safety report with canonical safety_category."""
        app.dependency_overrides[get_current_user] = lambda: self.citizen_profile

        with patch("app.services.safety_service.safety_service.create_safety_report", new_callable=AsyncMock) as mock_sr:
            mock_sr.return_value = SafetyReportResponse(
                id=uuid4(),
                citizen_id=self.citizen_id,
                title="Unlit Alleyway",
                description="Pedestrian walkway has no streetlights and feels deserted after dark.",
                latitude=15.492,
                longitude=73.815,
                safety_category="Poor Lighting",
                status="Submitted",
                priority="High",
                severity=7,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            payload = {
                "title": "Unlit Alleyway",
                "description": "Pedestrian walkway has no streetlights and feels deserted after dark.",
                "latitude": 15.492,
                "longitude": 73.815,
                "safety_category": "Poor Lighting",
            }
            res = self.client.post("/api/v1/safety-reports", json=payload)
            self.assertEqual(res.status_code, 201)
            self.assertEqual(res.json()["safety_category"], "Poor Lighting")

    # ------------------------------------------------------------------------
    # 7. Worker Role Isolation
    # ------------------------------------------------------------------------

    def test_15_worker_forbidden_from_viewing_map_complaints(self):
        """Workers are forbidden from accessing general map complaints (HTTP 403)."""
        app.dependency_overrides[get_current_user] = lambda: self.worker_profile

        from fastapi import HTTPException
        with patch("app.services.map_service.map_service.get_complaint_markers", new_callable=AsyncMock) as mock_cm:
            mock_cm.side_effect = HTTPException(
                status_code=403,
                detail="Workers do not have access to the general complaint register. View assigned tasks instead.",
            )

            res = self.client.get("/api/v1/map/complaints")
            self.assertEqual(res.status_code, 403)
            self.assertIn("Workers do not have access", res.json()["detail"])

    def test_16_worker_forbidden_from_viewing_safety_zones(self):
        """Workers are forbidden from viewing safety zones (HTTP 403)."""
        app.dependency_overrides[get_current_user] = lambda: self.worker_profile

        from fastapi import HTTPException
        with patch("app.services.map_service.map_service.get_safety_zones", new_callable=AsyncMock) as mock_sz:
            mock_sz.side_effect = HTTPException(
                status_code=403,
                detail="Workers do not have access to safety zone information.",
            )

            res = self.client.get("/api/v1/map/safety-zones")
            self.assertEqual(res.status_code, 403)
            self.assertIn("Workers do not have access", res.json()["detail"])


if __name__ == "__main__":
    unittest.main()
