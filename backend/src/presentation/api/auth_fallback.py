"""Fallback authentication endpoints.

This router is used when the full authentication stack (MongoDB + Beanie)
is unavailable. It provides a minimal `/auth/login` implementation that
supports the demo credentials so the frontend can operate in development
environments without the database.
"""

from datetime import datetime, timezone
import os
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

try:
    from ...infrastructure.auth_service import auth_service
except ImportError:  # pragma: no cover - if auth_service is missing we cannot proceed
    auth_service = None  # type: ignore


router = APIRouter(tags=["authentication"])


class LoginRequest(BaseModel):
    """Minimal login request payload."""

    email: EmailStr
    password: str = Field(..., min_length=1)
    remember_me: bool = False


class UserInfo(BaseModel):
    """User information returned to the frontend."""

    id: str
    email: EmailStr
    username: str
    full_name: str
    avatar_url: Optional[str] = None
    role: str = "user"
    is_verified: bool = True
    created_at: datetime


class AuthResponse(BaseModel):
    """Authentication response with token pair and user data."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800
    user: UserInfo


def _load_demo_user() -> Dict[str, Any]:
    """Load demo user configuration from environment variables.

    Returns a dictionary containing demo user information and stored password
    hash. The password is hashed using the same service employed in production
    so we can leverage the existing verification helpers.
    """

    email = os.getenv("DEMO_USER_EMAIL", "demo@example.com")
    password = os.getenv("DEMO_USER_PASSWORD", "Demo@123")
    username = os.getenv("DEMO_USER_USERNAME", "demo")
    full_name = os.getenv("DEMO_USER_FULLNAME", "Demo User")

    if auth_service is None:
        raise RuntimeError("Authentication service is not available")

    password_hash = auth_service.hash_password(password)

    return {
        "id": os.getenv("DEMO_USER_ID", "demo-user"),
        "email": email,
        "username": username,
        "full_name": full_name,
        "password_hash": password_hash,
        "avatar_url": os.getenv("DEMO_USER_AVATAR", None),
        "role": os.getenv("DEMO_USER_ROLE", "user"),
        "is_verified": True,
        "created_at": datetime.now(timezone.utc),
    }


_DEMO_USER_CACHE: Optional[Dict[str, Any]] = None


def _get_demo_user() -> Dict[str, Any]:
    """Return the cached demo user data."""

    global _DEMO_USER_CACHE
    if _DEMO_USER_CACHE is None:
        _DEMO_USER_CACHE = _load_demo_user()
    return _DEMO_USER_CACHE


def _verify_demo_credentials(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Validate credentials against the demo user."""

    user = _get_demo_user()
    if email.lower() != user["email"].lower():
        return None

    if not auth_service.verify_password(password, user["password_hash"]):
        return None

    return user


def _build_response(user: Dict[str, Any]) -> AuthResponse:
    """Generate JWT pair and response payload for the demo user."""

    tokens = auth_service.create_token_pair(user["id"], user["email"])

    expires_in = int(auth_service.access_token_expire.total_seconds())

    return AuthResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens.get("token_type", "bearer"),
        expires_in=expires_in,
        user=UserInfo(
            id=user["id"],
            email=user["email"],
            username=user["username"],
            full_name=user["full_name"],
            avatar_url=user.get("avatar_url"),
            role=user.get("role", "user"),
            is_verified=user.get("is_verified", True),
            created_at=user.get("created_at", datetime.now(timezone.utc)),
        ),
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest) -> AuthResponse:
    """Authenticate using the demo user credentials."""

    if auth_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    user = _verify_demo_credentials(request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return _build_response(user)


@router.post("/refresh")
async def refresh_token():
    """Indicate that refresh is not supported in fallback mode."""

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Token refresh is unavailable in fallback auth mode",
    )


@router.post("/register")
async def register_user():
    """Registrations are disabled in fallback auth mode."""

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Registration is unavailable in fallback auth mode",
    )
