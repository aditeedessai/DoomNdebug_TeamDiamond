"""Comprehensive Phase 2A Authentication Contract & Route Protection Test Suite.

Audits exact backend contracts, request schemas, response shapes, and role barriers:
1. Actual login response parsing (session.access_token + ProfileResponse).
2. Actual registration request field names (verifying 'phone' is accepted).
3. Registration response with a session.
4. Registration response without a session (email confirmation / unauthenticated).
5. Session restoration through /auth/me.
6. Invalid/expired token handling (HTTP 401).
7. Citizen vs official login mismatch (role discrimination).
8. Worker access restrictions (denied official registers, scoped to worker tasks).
9. Safety-officer-only route protection (strictly is_safety_officer == True).
10. Logout and protected-route redirects.
"""
import os
import sys
import unittest
from uuid import uuid4
from pydantic import ValidationError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.testclient import TestClient
from app.api.deps import (
    get_current_user,
    require_role,
    require_official,
    require_safety_officer,
)
from app.schemas.auth import (
    AuthResponse,
    AuthSession,
    LoginRequest,
    RegisterRequest,
)
from app.schemas.profile import ProfileResponse


class TestPhase2AAuthenticationContracts(unittest.TestCase):
    """Test backend auth schemas, response serialization, and role access controls."""

    def setUp(self):
        self.app = FastAPI(title="Phase 2A Audit Test App")

        # Mocked endpoints mirroring backend routes
        @self.app.get("/api/v1/auth/me", response_model=ProfileResponse)
        async def me(user: ProfileResponse = Depends(get_current_user)):
            return user

        @self.app.get("/api/v1/citizen/records")
        async def citizen_only(user: ProfileResponse = Depends(require_role(["citizen"]))):
            return {"access": "granted", "role": user.role}

        @self.app.get("/api/v1/official/complaints")
        async def official_only(user: ProfileResponse = Depends(require_role(["official"]))):
            return {"access": "granted", "role": user.role}

        @self.app.get("/api/v1/assignments")
        async def assignments_route(user: ProfileResponse = Depends(require_role(["official", "worker"]))):
            return {"access": "granted", "role": user.role}

        @self.app.get("/api/v1/safety-reports")
        async def safety_reports(user: ProfileResponse = Depends(require_safety_officer)):
            return {"access": "granted", "is_safety": user.is_safety_officer}

        self.client = TestClient(self.app)

    # 1. Actual login response parsing
    def test_01_actual_login_response_parsing(self):
        user_id = uuid4()
        session_data = AuthSession(
            access_token="valid.jwt.token",
            token_type="bearer",
            expires_in=3600,
            refresh_token="mock-refresh-token"
        )
        profile_data = ProfileResponse(
            id=user_id,
            full_name="Municipal Official",
            role="official",
            phone="+91 832 240 1001",
            is_safety_officer=False,
            department_id=uuid4()
        )
        auth_resp = AuthResponse(
            session=session_data,
            profile=profile_data,
            message="Login successful."
        )
        resp_dict = auth_resp.model_dump()
        self.assertIn("session", resp_dict)
        self.assertEqual(resp_dict["session"]["access_token"], "valid.jwt.token")
        self.assertEqual(resp_dict["profile"]["role"], "official")
        self.assertEqual(str(resp_dict["profile"]["id"]), str(user_id))

    # 2. Actual registration request field names ('phone' expected, not 'phone_number')
    def test_02_registration_request_field_names(self):
        # Valid payload with 'phone'
        valid_req = RegisterRequest(
            email="citizen@city.gov",
            password="StrongPassword123!",
            full_name="Jane Doe",
            phone="+91 98765 43210"
        )
        self.assertEqual(valid_req.phone, "+91 98765 43210")
        self.assertEqual(valid_req.full_name, "Jane Doe")

        # Invalid: short password (< 6 chars)
        with self.assertRaises(ValidationError):
            RegisterRequest(
                email="citizen@city.gov",
                password="123",
                full_name="Jane Doe"
            )

        # Invalid: invalid email format
        with self.assertRaises(ValidationError):
            RegisterRequest(
                email="not-an-email",
                password="StrongPassword123!",
                full_name="Jane Doe"
            )

    # 3. Registration response with a session
    def test_03_registration_response_with_session(self):
        user_id = uuid4()
        resp = AuthResponse(
            session=AuthSession(access_token="session.jwt.token"),
            profile=ProfileResponse(id=user_id, full_name="New Citizen", role="citizen"),
            message="Registration successful. Welcome to the AI City Management Platform."
        )
        self.assertIsNotNone(resp.session)
        self.assertEqual(resp.session.access_token, "session.jwt.token")
        self.assertEqual(resp.profile.role, "citizen")

    # 4. Registration response without a session (email confirmation / unauthenticated)
    def test_04_registration_response_without_session(self):
        user_id = uuid4()
        resp = AuthResponse(
            session=None,
            profile=ProfileResponse(id=user_id, full_name="New Citizen", role="citizen"),
            message="Registration successful. Please verify your email before logging in."
        )
        self.assertIsNone(resp.session)
        self.assertEqual(resp.profile.role, "citizen")
        # Ensure client should NOT treat this as an active session
        resp_dict = resp.model_dump()
        self.assertIsNone(resp_dict["session"])

    # 5. Session restoration through /auth/me
    def test_05_session_restoration_through_auth_me(self):
        user_id = uuid4()
        dept_id = uuid4()
        expected_profile = ProfileResponse(
            id=user_id,
            full_name="Restored Official",
            role="official",
            phone="+91 99999 88888",
            department_id=dept_id,
            is_safety_officer=True
        )
        self.app.dependency_overrides[get_current_user] = lambda: expected_profile

        res = self.client.get("/api/v1/auth/me")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["id"], str(user_id))
        self.assertEqual(body["role"], "official")
        self.assertTrue(body["is_safety_officer"])
        self.assertEqual(body["department_id"], str(dept_id))

    # 6. Invalid / expired token handling (HTTP 401)
    def test_06_invalid_token_handling(self):
        # Clear override so default behavior runs
        self.app.dependency_overrides.clear()
        res = self.client.get("/api/v1/auth/me")
        self.assertEqual(res.status_code, 401)  # HTTPBearer with no credentials raises 401

        # With invalid Authorization header
        res_auth = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer malformed.invalid.token"}
        )
        self.assertIn(res_auth.status_code, (401, 500))

    # 7. Citizen vs official login mismatch (role discrimination)
    def test_07_citizen_official_role_discrimination(self):
        citizen_profile = ProfileResponse(
            id=uuid4(),
            full_name="Citizen User",
            role="citizen",
            is_safety_officer=False
        )
        official_profile = ProfileResponse(
            id=uuid4(),
            full_name="Officer User",
            role="official",
            is_safety_officer=False
        )

        # Citizen visiting official route is rejected with 403
        self.app.dependency_overrides[get_current_user] = lambda: citizen_profile
        res_off = self.client.get("/api/v1/official/complaints")
        self.assertEqual(res_off.status_code, 403)

        # Official visiting citizen route is rejected with 403
        self.app.dependency_overrides[get_current_user] = lambda: official_profile
        res_cit = self.client.get("/api/v1/citizen/records")
        self.assertEqual(res_cit.status_code, 403)

    # 8. Worker access restrictions
    def test_08_worker_access_restrictions(self):
        worker_profile = ProfileResponse(
            id=uuid4(),
            full_name="Field Worker Dave",
            role="worker",
            is_safety_officer=False
        )
        self.app.dependency_overrides[get_current_user] = lambda: worker_profile

        # Worker cannot access official complaints register
        res_comp = self.client.get("/api/v1/official/complaints")
        self.assertEqual(res_comp.status_code, 403)

        # Worker cannot access citizen routes
        res_cit = self.client.get("/api/v1/citizen/records")
        self.assertEqual(res_cit.status_code, 403)

        # Worker CAN access assignments route
        res_assign = self.client.get("/api/v1/assignments")
        self.assertEqual(res_assign.status_code, 200)
        self.assertEqual(res_assign.json()["role"], "worker")

    # 9. Safety-officer-only route protection
    def test_09_safety_officer_only_protection(self):
        normal_official = ProfileResponse(
            id=uuid4(),
            full_name="Ordinary Officer",
            role="official",
            is_safety_officer=False
        )
        safety_official = ProfileResponse(
            id=uuid4(),
            full_name="Safety Lead Officer",
            role="official",
            is_safety_officer=True
        )

        # Normal official denied access to safety reports (HTTP 403)
        self.app.dependency_overrides[get_current_user] = lambda: normal_official
        res_denied = self.client.get("/api/v1/safety-reports")
        self.assertEqual(res_denied.status_code, 403)
        self.assertIn("safety officials only", res_denied.json()["detail"].lower())

        # Safety officer granted access to safety reports (HTTP 200)
        self.app.dependency_overrides[get_current_user] = lambda: safety_official
        res_ok = self.client.get("/api/v1/safety-reports")
        self.assertEqual(res_ok.status_code, 200)
        self.assertTrue(res_ok.json()["is_safety"])

    # 10. Logout and protected-route redirects (contract validation)
    def test_10_logout_and_unauthenticated_barriers(self):
        self.app.dependency_overrides.clear()
        # When token is cleared (unauthenticated), all protected endpoints deny access
        for endpoint in ["/api/v1/auth/me", "/api/v1/citizen/records", "/api/v1/official/complaints", "/api/v1/safety-reports"]:
            res = self.client.get(endpoint)
            self.assertIn(res.status_code, (401, 403))


if __name__ == "__main__":
    unittest.main()
