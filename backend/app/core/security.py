"""Security and authentication utilities for Supabase JWT verification."""
from typing import Any, Dict, Optional
from fastapi import HTTPException, status

from app.core.config import settings
from app.database.supabase import supabase_service

try:
    import jwt
    HAS_PYJWT = True
except ImportError:
    HAS_PYJWT = False


async def verify_jwt_token(token: str) -> Dict[str, Any]:
    """Verify Supabase JWT token.

    Primary approach: Verifies with Supabase Auth service directly via get_user_from_token.
    This supports asymmetric algorithms (RS256/ES256), symmetric (HS256), and real-time revocation.
    Fallback approach: Decodes locally with PyJWT if SUPABASE_JWT_SECRET is configured.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. Primary: Verify via Supabase Auth API
    user_data = await supabase_service.get_user_from_token(token)
    if user_data and "id" in user_data:
        return user_data

    # 2. Fallback: Local verification if secret is provided and PyJWT is available
    if HAS_PYJWT and settings.SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
            return {"id": payload.get("sub"), "email": payload.get("email"), "user_metadata": payload.get("user_metadata", {})}
        except Exception:
            pass

    # If Supabase is unconfigured (e.g. running in local development mode without keys),
    # return error indicating unconfigured or invalid token
    if not supabase_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not configured. Please supply SUPABASE_URL and SUPABASE_ANON_KEY.",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )

