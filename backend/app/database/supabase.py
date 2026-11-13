"""Supabase database and client initialization.

Provides both PostgREST / Auth client utilities via HTTP and wraps supabase-py
when available. Does not fail on startup if Supabase credentials are not yet configured.
"""
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings

# Attempt to import official supabase client if installed
try:
    from supabase import create_client as _create_supabase_client, Client
    HAS_SUPABASE_SDK = True
except ImportError:
    Client = Any  # type: ignore
    HAS_SUPABASE_SDK = False


class SupabaseService:
    """Service wrapper for interacting with Supabase Auth and PostgREST APIs."""

    def __init__(self):
        self.url = (settings.SUPABASE_URL or "").rstrip("/")
        self.anon_key = settings.SUPABASE_ANON_KEY or ""
        self.service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY or ""

    @property
    def is_configured(self) -> bool:
        """Check if Supabase endpoint and keys are provided."""
        return bool(self.url and (self.anon_key or self.service_role_key))

    def _get_headers(self, token: Optional[str] = None, use_service_role: bool = False) -> Dict[str, str]:
        """Build standard Supabase headers for API calls."""
        key = self.service_role_key if use_service_role and self.service_role_key else self.anon_key
        headers = {
            "apikey": key,
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        elif use_service_role and self.service_role_key:
            headers["Authorization"] = f"Bearer {self.service_role_key}"
        return headers

    async def get_user_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT and retrieve user profile from Supabase Auth service."""
        if not self.is_configured:
            return None

        endpoint = f"{self.url}/auth/v1/user"
        headers = {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {token}",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(endpoint, headers=headers)
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return None

    async def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch user profile row from the public.profiles table."""
        if not self.is_configured:
            return None

        endpoint = f"{self.url}/rest/v1/profiles?id=eq.{user_id}&select=*"
        headers = self._get_headers(use_service_role=True)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(endpoint, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        return data[0]
        except Exception:
            pass
        return None

    async def sign_in_with_password(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with email and password via Supabase Auth."""
        if not self.is_configured:
            return None

        endpoint = f"{self.url}/auth/v1/token?grant_type=password"
        headers = {"apikey": self.anon_key, "Content-Type": "application/json"}
        payload = {"email": email, "password": password}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(endpoint, json=payload, headers=headers)
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return None

    async def sign_up_citizen(self, email: str, password: str, full_name: str, phone: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Register a new citizen through Supabase Auth (trigger handles profile creation)."""
        if not self.is_configured:
            return None

        endpoint = f"{self.url}/auth/v1/signup"
        headers = {"apikey": self.anon_key, "Content-Type": "application/json"}
        payload = {
            "email": email,
            "password": password,
            "data": {
                "full_name": full_name,
                "role": "citizen",  # Enforce citizen role in user metadata
            }
        }
        if phone:
            payload["data"]["phone"] = phone
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(endpoint, json=payload, headers=headers)
                if resp.status_code in (200, 201):
                    return resp.json()
        except Exception:
            pass
        return None


# Global service instance
supabase_service = SupabaseService()
