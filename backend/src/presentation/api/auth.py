"""Authentication API endpoints."""

import hashlib
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from pydantic import BaseModel, EmailStr, Field
try:
    from loguru import logger
except ImportError:  # pragma: no cover - optional dependency
    import logging

    logger = logging.getLogger(__name__)

from ...domain.auth.models import User, RefreshToken, LoginAttempt, PasswordResetToken
from ...infrastructure.auth.jwt_service import jwt_service
from ...infrastructure.auth.password_service import password_service
from ...infrastructure.auth.middleware import get_current_user, get_current_verified_user


router = APIRouter(prefix="/auth", tags=["authentication"])


# Request/Response schemas
class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str
    new_password: str = Field(..., min_length=8)


class ResetPasswordRequest(BaseModel):
    """Reset password request."""
    email: EmailStr


class ResetPasswordConfirm(BaseModel):
    """Reset password confirmation."""
    token: str
    new_password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """User response."""
    user_id: str
    email: str
    username: str
    full_name: Optional[str]
    roles: list[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    avatar_url: Optional[str]


@router.post("/register", response_model=UserResponse)
async def register(request: RegisterRequest):
    """Register new user."""
    # Check if user exists
    existing_user = await User.find_one(
        (User.email == request.email) | (User.username == request.username)
    )

    if existing_user:
        if existing_user.email == request.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

    # Validate password strength
    is_valid, error_message = password_service.validate_password_strength(request.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    # Create new user
    user = User(
        email=request.email,
        username=request.username,
        password_hash=password_service.hash_password(request.password),
        full_name=request.full_name
    )

    await user.insert()
    logger.info(f"New user registered: {user.email}")

    # TODO: Send verification email

    return UserResponse(**user.to_dict())


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, req: Request):
    """User login."""
    # Track login attempt
    attempt = LoginAttempt(
        email=request.email,
        ip_address=req.client.host if req.client else "unknown",
        user_agent=req.headers.get("user-agent"),
        success=False
    )

    # Find user
    user = await User.find_one(User.email == request.email)

    if not user:
        attempt.failure_reason = "User not found"
        await attempt.insert()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Check if account is locked
    if user.is_locked():
        attempt.failure_reason = "Account locked"
        await attempt.insert()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is locked. Please try again later."
        )

    # Verify password
    if not password_service.verify_password(request.password, user.password_hash):
        user.increment_failed_login()
        await user.save()

        attempt.failure_reason = "Invalid password"
        await attempt.insert()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Check if account is active
    if not user.is_active:
        attempt.failure_reason = "Account inactive"
        await attempt.insert()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    # Update login info
    user.update_last_login()
    await user.save()

    # Record successful attempt
    attempt.success = True
    await attempt.insert()

    # Create tokens
    token_data = {
        "sub": user.user_id,
        "email": user.email,
        "username": user.username,
        "roles": user.roles
    }

    tokens = jwt_service.create_token_pair(token_data)

    # Store refresh token
    refresh_token_hash = hashlib.sha256(tokens["refresh_token"].encode()).hexdigest()
    refresh_token_doc = RefreshToken(
        user_id=user.user_id,
        token_hash=refresh_token_hash,
        expires_at=datetime.utcnow() + timedelta(days=jwt_service.refresh_token_expire_days),
        device_info=req.headers.get("user-agent"),
        ip_address=req.client.host if req.client else "unknown"
    )
    await refresh_token_doc.insert()

    logger.info(f"User logged in: {user.email}")

    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=jwt_service.access_token_expire_minutes * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    """Refresh access token."""
    # Verify refresh token
    try:
        payload = jwt_service.verify_refresh_token(request.refresh_token)
    except HTTPException as e:
        raise e

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    # Check if refresh token is stored and valid
    token_hash = hashlib.sha256(request.refresh_token.encode()).hexdigest()
    stored_token = await RefreshToken.find_one(
        (RefreshToken.token_hash == token_hash) &
        (RefreshToken.user_id == user_id)
    )

    if not stored_token or not stored_token.is_valid():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Get user
    user = await User.find_one(User.user_id == user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Update token usage
    stored_token.update_usage()
    await stored_token.save()

    # Create new access token
    token_data = {
        "sub": user.user_id,
        "email": user.email,
        "username": user.username,
        "roles": user.roles
    }

    new_access_token = jwt_service.create_access_token(token_data)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=request.refresh_token,  # Return same refresh token
        token_type="bearer",
        expires_in=jwt_service.access_token_expire_minutes * 60
    )


@router.post("/logout")
async def logout(
    refresh_token: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Logout user."""
    if refresh_token:
        # Revoke refresh token
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        stored_token = await RefreshToken.find_one(
            (RefreshToken.token_hash == token_hash) &
            (RefreshToken.user_id == current_user.user_id)
        )

        if stored_token:
            stored_token.revoke("User logout")
            await stored_token.save()

    logger.info(f"User logged out: {current_user.email}")

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse(**current_user.to_dict())


@router.put("/me")
async def update_current_user(
    full_name: Optional[str] = None,
    avatar_url: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Update current user information."""
    if full_name is not None:
        current_user.full_name = full_name

    if avatar_url is not None:
        current_user.avatar_url = avatar_url

    current_user.updated_at = datetime.utcnow()
    await current_user.save()

    return UserResponse(**current_user.to_dict())


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user)
):
    """Change user password."""
    # Verify current password
    if not password_service.verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Validate new password
    is_valid, error_message = password_service.validate_password_strength(request.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    # Update password
    current_user.password_hash = password_service.hash_password(request.new_password)
    current_user.updated_at = datetime.utcnow()
    await current_user.save()

    # Revoke all refresh tokens
    tokens = await RefreshToken.find(
        (RefreshToken.user_id == current_user.user_id) &
        (RefreshToken.revoked == False)
    ).to_list()

    for token in tokens:
        token.revoke("Password changed")
        await token.save()

    logger.info(f"Password changed for user: {current_user.email}")

    return {"message": "Password changed successfully"}


@router.post("/reset-password")
async def request_password_reset(request: ResetPasswordRequest):
    """Request password reset."""
    user = await User.find_one(User.email == request.email)

    # Don't reveal if user exists
    if not user:
        return {"message": "If the email exists, a reset link has been sent"}

    # Create reset token
    import secrets
    token_string = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token_string.encode()).hexdigest()

    reset_token = PasswordResetToken(
        user_id=user.user_id,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    await reset_token.insert()

    # TODO: Send reset email with token_string

    logger.info(f"Password reset requested for: {user.email}")

    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password/confirm")
async def confirm_password_reset(request: ResetPasswordConfirm):
    """Confirm password reset."""
    # Find token
    token_hash = hashlib.sha256(request.token.encode()).hexdigest()
    reset_token = await PasswordResetToken.find_one(
        PasswordResetToken.token_hash == token_hash
    )

    if not reset_token or not reset_token.is_valid():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Get user
    user = await User.find_one(User.user_id == reset_token.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )

    # Validate new password
    is_valid, error_message = password_service.validate_password_strength(request.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    # Update password
    user.password_hash = password_service.hash_password(request.new_password)
    user.updated_at = datetime.utcnow()
    await user.save()

    # Mark token as used
    reset_token.mark_used()
    await reset_token.save()

    # Revoke all refresh tokens
    tokens = await RefreshToken.find(
        (RefreshToken.user_id == user.user_id) &
        (RefreshToken.revoked == False)
    ).to_list()

    for token in tokens:
        token.revoke("Password reset")
        await token.save()

    logger.info(f"Password reset completed for: {user.email}")

    return {"message": "Password reset successfully"}


@router.post("/verify-email")
async def verify_email(
    token: str,
    current_user: User = Depends(get_current_user)
):
    """Verify user email."""
    # TODO: Implement email verification logic

    current_user.email_verified = True
    current_user.is_verified = True
    await current_user.save()

    return {"message": "Email verified successfully"}
