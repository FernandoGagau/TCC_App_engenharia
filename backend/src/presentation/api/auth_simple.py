"""
Simple Authentication API - Self-contained
Following SOLID principles but without complex imports
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Dict, Any, Optional
import hashlib
import secrets
import time
from datetime import datetime, timezone

# Create router
router = APIRouter(tags=["auth"])

# Demo users storage
DEMO_USERS = {
    "demo@example.com": {
        "id": "demo-user-001",
        "email": "demo@example.com",
        "username": "demo",
        "full_name": "Demo User",
        "password_hash": "ff96673205dc722320598ebf8f88325b2ac56922d5a2164b5765868274bc0d73",  # Demo@123
        "role": "user",
        "is_verified": True,
        "is_active": True,
        "avatar_url": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
}


# Request/Response Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 43200  # 12 hours in seconds
    user: Dict[str, Any]


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: str
    avatar_url: str = None
    role: str
    is_verified: bool


# Helper functions - Following Single Responsibility Principle
def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == hashed


def create_token(prefix: str) -> str:
    """Create a token with given prefix"""
    timestamp = int(time.time())
    return f"{prefix}_{secrets.token_urlsafe(32)}_{timestamp}"


def find_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Find user by email"""
    return DEMO_USERS.get(email.lower())


def create_user(email: str, password: str, username: str, full_name: str) -> Dict[str, Any]:
    """Create new user"""
    user_id = f"user-{int(time.time())}"
    new_user = {
        "id": user_id,
        "email": email,
        "username": username,
        "full_name": full_name,
        "password_hash": hash_password(password),
        "role": "user",
        "is_verified": True,
        "is_active": True,
        "avatar_url": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    DEMO_USERS[email] = new_user
    return new_user


# API Endpoints
@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest) -> AuthResponse:
    """User login endpoint"""
    try:
        # Find user
        user = find_user_by_email(request.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Verify password
        if not verify_password(request.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Check if user is active
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )

        # Create tokens
        access_token = create_token("access")
        refresh_token = create_token("refresh")

        # Build response
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=43200,  # 12 hours
            user={
                "id": user["id"],
                "email": user["email"],
                "username": user["username"],
                "full_name": user["full_name"],
                "avatar_url": user.get("avatar_url"),
                "role": user.get("role", "user"),
                "is_verified": user.get("is_verified", True)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest) -> AuthResponse:
    """User registration endpoint"""
    try:
        # Check if user already exists
        if find_user_by_email(request.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

        # Create user
        user = create_user(
            email=request.email,
            password=request.password,
            username=request.username,
            full_name=request.full_name
        )

        # Create tokens
        access_token = create_token("access")
        refresh_token = create_token("refresh")

        # Build response
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=43200,  # 12 hours
            user={
                "id": user["id"],
                "email": user["email"],
                "username": user["username"],
                "full_name": user["full_name"],
                "avatar_url": user.get("avatar_url"),
                "role": user.get("role", "user"),
                "is_verified": user.get("is_verified", True)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user() -> UserResponse:
    """Get current user information"""
    try:
        demo_user = DEMO_USERS["demo@example.com"]
        return UserResponse(
            id=demo_user["id"],
            email=demo_user["email"],
            username=demo_user["username"],
            full_name=demo_user["full_name"],
            avatar_url=demo_user.get("avatar_url"),
            role=demo_user.get("role", "user"),
            is_verified=demo_user.get("is_verified", True)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    """User logout"""
    return


@router.post("/refresh")
async def refresh_token():
    """Refresh access token"""
    new_access_token = create_token("access")
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": 43200  # 12 hours
    }