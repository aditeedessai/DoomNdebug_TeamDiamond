"""Unit and contract verification for Phase 2 Auth Integration."""
import os
import sys
import unittest
from uuid import uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.testclient import TestClient
from app.api.deps import get_current_user, require_role, require_official, require_safety_officer
from app.schemas.profile import ProfileResponse
from app.schemas.auth import AuthResponse, AuthSession

class TestPhase2AuthContract(unittest.TestCase):
    """Test auth contract and role barriers."""

    def setUp(self):
        self.app = FastAPI()
        
        # Test endpoints mirroring routes
        @self.app.get("/api/v1/auth/me", response_model=ProfileResponse)
        async def me(user: ProfileResponse = Depends(get_current_user)):
            return user

        @self.app.get("/api/v1/citizen/records")
        async def citizen_route(user: ProfileResponse = Depends(require_role(["citizen"]))):
            return {"access": "granted", "role": user.role}

        @self.app.get("/api/v1/official/triage")
        async def official_route(user: ProfileResponse = Depends(require_official)):
            return {"access": "granted", "role": user.role}

        @self.app.get("/api/v1/safety/register")
        async def safety_route(user: ProfileResponse = Depends(require_safety_officer)):
            return {"access": "granted", "is_safety": user.is_safety_officer}

        self.client = TestClient(self.app)

    def test_unauthenticated_rejected(self):
        res = self.client.get("/api/v1/auth/me")
        self.assertEqual(res.status_code, 401)

    def test_citizen_access_and_official_denial(self):
        citizen_user = ProfileResponse(
            id=uuid4(),
            full_name="Jane Citizen",
            role="citizen",
            is_safety_officer=False
        )
        self.app.dependency_overrides[get_current_user] = lambda: citizen_user

        # Citizen route succeeds
        res = self.client.get("/api/v1/citizen/records")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["role"], "citizen")

        # Official route forbidden for citizen
        res_off = self.client.get("/api/v1/official/triage")
        self.assertEqual(res_off.status_code, 403)

        # Safety register forbidden for citizen
        res_safe = self.client.get("/api/v1/safety/register")
        self.assertEqual(res_safe.status_code, 403)

    def test_official_access_and_citizen_denial(self):
        official_user = ProfileResponse(
            id=uuid4(),
            full_name="Officer Dave",
            role="official",
            is_safety_officer=False
        )
        self.app.dependency_overrides[get_current_user] = lambda: official_user

        # Official route succeeds
        res = self.client.get("/api/v1/official/triage")
        self.assertEqual(res.status_code, 200)

        # Citizen route forbidden for official
        res_cit = self.client.get("/api/v1/citizen/records")
        self.assertEqual(res_cit.status_code, 403)

        # Safety route forbidden for ordinary official
        res_safe = self.client.get("/api/v1/safety/register")
        self.assertEqual(res_safe.status_code, 403)

    def test_safety_officer_access(self):
        safety_user = ProfileResponse(
            id=uuid4(),
            full_name="Safety Lead Sarah",
            role="official",
            is_safety_officer=True
        )
        self.app.dependency_overrides[get_current_user] = lambda: safety_user

        res_safe = self.client.get("/api/v1/safety/register")
        self.assertEqual(res_safe.status_code, 200)
        self.assertTrue(res_safe.json()["is_safety"])

if __name__ == "__main__":
    unittest.main()
