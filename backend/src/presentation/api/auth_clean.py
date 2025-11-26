"""
Clean Authentication API
Following SOLID principles and clean architecture
Single Responsibility: Handle HTTP auth requests only
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Dict, Any

# Import our clean architecture components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from domain.auth.entities import AuthCredentials, AuthResponse
from application.auth.authentication_service import DemoAuthenticationService
from infrastructure.auth.demo_repository import DemoUserRepository
from infrastructure.auth.simple_password_service import SimplePasswordService
from infrastructure.auth.token_service import SimpleTokenService

# Create router
router = APIRouter(tags=["auth"])

# Initialize services (Dependency Injection)
user_repository = DemoUserRepository()
password_service = SimplePasswordService()
token_service = SimpleTokenService()
auth_service = DemoAuthenticationService(
    user_repository=user_repository,
    password_service=password_service,
    token_service=token_service
)


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


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: str
    avatar_url: str = None
    role: str
    is_verified: bool


# API Endpoints
@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest) -> AuthResponse:
    """User login endpoint"""
    try:
        # Authenticate user
        user = await auth_service.authenticate_user(request.email, request.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Create tokens
        tokens = auth_service.create_auth_tokens(user)

        # Build response
        return AuthResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type=tokens["token_type"],
            expires_in=1800,
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
        existing_user = await user_repository.find_by_email(request.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

        # Create user
        user = await auth_service.create_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            username=request.username
        )

        # Create tokens
        tokens = auth_service.create_auth_tokens(user)

        # Build response
        return AuthResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type=tokens["token_type"],
            expires_in=1800,
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
    # For demo purposes, return demo user
    return UserResponse(
        id="demo-user-001",
        email="demo@example.com",
        username="demo",
        full_name="Demo User",
        role="user",
        is_verified=True
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    """User logout"""
    return


@router.post("/refresh")
async def refresh_token():
    """Refresh access token"""
    new_access_token = token_service.create_access_token("demo-user-001", "demo@example.com")
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": 1800
    }