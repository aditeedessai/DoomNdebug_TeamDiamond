"""FastAPI dependency injection utilities for authentication and authorization."""
from typing import List, Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_jwt_token
from app.database.supabase import supabase_service
from app.schemas.profile import ProfileResponse, UserRole

# HTTP Bearer scheme
bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> ProfileResponse:
    """Validate Bearer token and retrieve the authenticated user's profile."""
    token = credentials.credentials
    user_payload = await verify_jwt_token(token)
    user_id = user_payload.get("id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token does not contain a valid user identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch stored profile from database
    profile_data = await supabase_service.get_profile(user_id)

    if profile_data:
        return ProfileResponse(**profile_data)

    # Fallback if profile row is still syncing from trigger
    meta = user_payload.get("user_metadata", {})
    return ProfileResponse(
        id=UUID(user_id),
        full_name=meta.get("full_name", meta.get("name", "Citizen User")),
        role=meta.get("role", "citizen"),
        department_id=meta.get("department_id"),
        is_safety_officer=meta.get("is_safety_officer", False),
        phone=user_payload.get("phone", meta.get("phone")),
    )


def require_role(allowed_roles: List[UserRole]):
    """Factory dependency to enforce role-based access control."""
    async def role_checker(
        current_user: ProfileResponse = Depends(get_current_user)
    ) -> ProfileResponse:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Required role in {allowed_roles}, your role is '{current_user.role}'",
            )
        return current_user

    return role_checker


async def require_official(
    current_user: ProfileResponse = Depends(require_role(["official"]))
) -> ProfileResponse:
    """Dependency verifying that the user is an official."""
    return current_user


async def require_safety_officer(
    current_user: ProfileResponse = Depends(require_role(["official"]))
) -> ProfileResponse:
    """Dependency verifying that the official is explicitly authorized for safety reports."""
    if not current_user.is_safety_officer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Restricted to designated safety officials only",
        )
    return current_user


def require_department(target_department_id: UUID):
    """Enforce that the official belongs to the specified department (or is a general officer)."""
    async def department_checker(
        current_user: ProfileResponse = Depends(require_official)
    ) -> ProfileResponse:
        if current_user.department_id and current_user.department_id != target_department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not authorized for this municipal department",
            )
        return current_user

    return department_checker

