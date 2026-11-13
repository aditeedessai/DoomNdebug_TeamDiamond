"""Authentication endpoints for citizen signup, login, and profile retrieval."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.database.supabase import supabase_service
from app.schemas.auth import AuthResponse, AuthSession, LoginRequest, RegisterRequest
from app.schemas.profile import ProfileResponse

router = APIRouter()


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new citizen account",
)
async def register_citizen(request: RegisterRequest):
    """Citizen self-registration endpoint.

    Role is strictly defaulted to 'citizen'. Official and worker accounts must be provisioned
    through secure administrative channels.
    """
    if not supabase_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase service is not configured. Please provide SUPABASE_URL and SUPABASE_ANON_KEY.",
        )

    result = await supabase_service.sign_up_citizen(
        email=request.email,
        password=request.password,
        full_name=request.full_name,
        phone=request.phone,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to register citizen account. The email may already be registered or the password is weak.",
        )

    user = result.get("user") or {}
    session = result.get("session")
    user_id = user.get("id")

    # Fetch newly created profile or construct from returned user
    profile_data = await supabase_service.get_profile(user_id) if user_id else None
    if profile_data:
        profile = ProfileResponse(**profile_data)
    else:
        profile = ProfileResponse(
            id=UUID(user_id),
            full_name=request.full_name,
            role="citizen",
            phone=request.phone,
        )

    auth_session = None
    if session and "access_token" in session:
        auth_session = AuthSession(
            access_token=session["access_token"],
            token_type=session.get("token_type", "bearer"),
            expires_in=session.get("expires_in"),
            refresh_token=session.get("refresh_token"),
        )

    return AuthResponse(
        session=auth_session,
        profile=profile,
        message="Registration successful. Welcome to the AI City Management Platform.",
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Log in with email and password",
)
async def login_user(request: LoginRequest):
    """Authenticate citizen, official, or worker using Supabase credentials."""
    if not supabase_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase service is not configured. Please provide SUPABASE_URL and SUPABASE_ANON_KEY.",
        )

    result = await supabase_service.sign_in_with_password(
        email=request.email,
        password=request.password,
    )

    if not result or "access_token" not in result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = result.get("user") or {}
    user_id = user.get("id")

    profile_data = await supabase_service.get_profile(user_id) if user_id else None
    if profile_data:
        profile = ProfileResponse(**profile_data)
    else:
        meta = user.get("user_metadata", {})
        profile = ProfileResponse(
            id=UUID(user_id),
            full_name=meta.get("full_name", meta.get("name", "User")),
            role=meta.get("role", "citizen"),
            department_id=meta.get("department_id"),
            is_safety_officer=meta.get("is_safety_officer", False),
            phone=user.get("phone", meta.get("phone")),
        )

    auth_session = AuthSession(
        access_token=result["access_token"],
        token_type=result.get("token_type", "bearer"),
        expires_in=result.get("expires_in"),
        refresh_token=result.get("refresh_token"),
    )

    return AuthResponse(
        session=auth_session,
        profile=profile,
        message="Login successful.",
    )


@router.get(
    "/me",
    response_model=ProfileResponse,
    summary="Retrieve current user profile",
)
async def get_my_profile(
    current_user: ProfileResponse = Depends(get_current_user),
):
    """Fetch the authenticated user's profile and active role."""
    return current_user

