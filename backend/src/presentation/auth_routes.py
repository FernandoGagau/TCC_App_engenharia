"""
Authentication API Routes
Handles user registration, login, logout, and token refresh
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import logging
import hashlib
import secrets

from ..infrastructure.auth_service import auth_service
from ..domain.auth_models_mongo import User, RefreshToken, LoginAttempt, PasswordHistory

logger = logging.getLogger(__name__)

router = APIRouter(tags=["authentication"])
security = HTTPBearer()

# Request/Response Models
class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=30)
    full_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8)
    confirm_password: str

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class ResetPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30 minutes
    user: Dict[str, Any]


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: str
    avatar_url: Optional[str]
    role: str
    is_verified: bool
    created_at: datetime


# Helper functions
def get_client_info(request: Request) -> Dict[str, str]:
    """Extract client information from request"""
    return {
        'ip_address': request.client.host if request.client else None,
        'user_agent': request.headers.get('user-agent', ''),
        'browser': extract_browser(request.headers.get('user-agent', '')),
    }


def extract_browser(user_agent: str) -> str:
    """Extract browser name from user agent"""
    if 'Chrome' in user_agent:
        return 'Chrome'
    elif 'Firefox' in user_agent:
        return 'Firefox'
    elif 'Safari' in user_agent:
        return 'Safari'
    elif 'Edge' in user_agent:
        return 'Edge'
    return 'Unknown'


def hash_token(token: str) -> str:
    """Hash a token for storage"""
    return hashlib.sha256(token.encode()).hexdigest()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    payload = auth_service.validate_access_token(token)

    user = await User.get(payload['sub'])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    return user


# API Endpoints
@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, req: Request):
    """Register a new user"""
    try:
        # Check if email already exists
        existing_user = await User.find_one(User.email == request.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

        # Check if username already exists
        existing_user = await User.find_one(User.username == request.username.lower())
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken"
            )

        # Validate email format
        if not auth_service.validate_email(request.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )

        # Validate password strength
        is_valid, error_msg = auth_service.validate_password_strength(request.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # Create new user
        user = User(
            email=request.email,
            username=request.username.lower(),
            full_name=request.full_name,
            password_hash=auth_service.hash_password(request.password)
        )

        # Generate verification token
        user.generate_verification_token()

        # Save user
        await user.insert()

        # Generate tokens
        tokens = auth_service.create_token_pair(str(user.id), user.email)

        # Create refresh token record
        client_info = get_client_info(req)
        refresh_token = RefreshToken(
            token_id=auth_service.decode_token(tokens['refresh_token'])['jti'],
            user_id=str(user.id),
            token_hash=hash_token(tokens['refresh_token']),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            **client_info
        )
        await refresh_token.insert()

        # Log successful registration
        await LoginAttempt(
            email=user.email,
            success=True,
            **client_info
        ).insert()

        return AuthResponse(
            access_token=tokens['access_token'],
            refresh_token=tokens['refresh_token'],
            token_type=tokens['token_type'],
            user={
                'id': str(user.id),
                'email': user.email,
                'username': user.username,
                'full_name': user.full_name,
                'role': user.role,
                'is_verified': user.is_verified
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, req: Request):
    """User login"""
    try:
        client_info = get_client_info(req)

        # Find user by email
        user = await User.find_one(User.email == request.email)

        if not user:
            # Log failed attempt
            await LoginAttempt(
                email=request.email,
                success=False,
                failure_reason="User not found",
                **client_info
            ).insert()

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Check if account is locked
        if user.is_locked():
            await LoginAttempt(
                email=request.email,
                success=False,
                failure_reason="Account locked",
                **client_info
            ).insert()

            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is temporarily locked due to multiple failed login attempts"
            )

        # Verify password
        if not auth_service.verify_password(request.password, user.password_hash):
            user.record_failed_login()
            await user.save()

            await LoginAttempt(
                email=request.email,
                success=False,
                failure_reason="Invalid password",
                **client_info
            ).insert()

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Check if account is active
        if not user.is_active:
            await LoginAttempt(
                email=request.email,
                success=False,
                failure_reason="Account disabled",
                **client_info
            ).insert()

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )

        # Generate tokens
        tokens = auth_service.create_token_pair(str(user.id), user.email)

        # Adjust refresh token expiry based on remember_me
        refresh_expiry = timedelta(days=30 if request.remember_me else 7)

        # Create refresh token record
        refresh_token = RefreshToken(
            token_id=auth_service.decode_token(tokens['refresh_token'])['jti'],
            user_id=str(user.id),
            token_hash=hash_token(tokens['refresh_token']),
            expires_at=datetime.now(timezone.utc) + refresh_expiry,
            **client_info
        )
        await refresh_token.insert()

        # Update user login info
        user.record_successful_login(client_info['ip_address'])
        await user.save()

        # Log successful login
        await LoginAttempt(
            email=user.email,
            success=True,
            **client_info
        ).insert()

        return AuthResponse(
            access_token=tokens['access_token'],
            refresh_token=tokens['refresh_token'],
            token_type=tokens['token_type'],
            user={
                'id': str(user.id),
                'email': user.email,
                'username': user.username,
                'full_name': user.full_name,
                'avatar_url': user.avatar_url,
                'role': user.role,
                'is_verified': user.is_verified
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(request: RefreshTokenRequest, req: Request):
    """Refresh access token"""
    try:
        # Validate refresh token
        payload = auth_service.validate_refresh_token(request.refresh_token)

        # Find refresh token record
        token_record = await RefreshToken.find_one(
            RefreshToken.token_id == payload['jti'],
            RefreshToken.user_id == payload['sub']
        )

        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Check if token is valid
        if not token_record.is_valid():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired or revoked"
            )

        # Get user
        user = await User.get(payload['sub'])
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        # Generate new tokens
        tokens = auth_service.create_token_pair(str(user.id), user.email)

        # Update refresh token record
        token_record.last_used = datetime.now(timezone.utc)
        token_record.use_count += 1
        await token_record.save()

        return AuthResponse(
            access_token=tokens['access_token'],
            refresh_token=request.refresh_token,  # Keep same refresh token
            token_type=tokens['token_type'],
            user={
                'id': str(user.id),
                'email': user.email,
                'username': user.username,
                'full_name': user.full_name,
                'avatar_url': user.avatar_url,
                'role': user.role,
                'is_verified': user.is_verified
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user: User = Depends(get_current_user)):
    """Logout user and revoke all refresh tokens"""
    try:
        # Revoke all user refresh tokens
        await RefreshToken.revoke_all_user_tokens(str(current_user.id))
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        role=current_user.role,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at
    )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request: ChangePasswordRequest,
    req: Request,
    current_user: User = Depends(get_current_user)
):
    """Change user password"""
    try:
        # Verify current password
        if not auth_service.verify_password(request.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        # Validate new password strength
        is_valid, error_msg = auth_service.validate_password_strength(request.new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # Check password history
        new_hash = auth_service.hash_password(request.new_password)
        if await PasswordHistory.check_password_reuse(str(current_user.id), new_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reuse recent passwords"
            )

        # Update password
        current_user.password_hash = new_hash
        await current_user.save()

        # Save to password history
        client_info = get_client_info(req)
        await PasswordHistory(
            user_id=str(current_user.id),
            password_hash=new_hash,
            changed_by_ip=client_info['ip_address']
        ).insert()

        # Revoke all refresh tokens for security
        await RefreshToken.revoke_all_user_tokens(str(current_user.id), "Password changed")

        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def request_password_reset(request: ResetPasswordRequest):
    """Request password reset token"""
    try:
        user = await User.find_one(User.email == request.email)

        # Don't reveal if user exists
        if user:
            # Generate reset token
            reset_token = user.generate_reset_token()
            await user.save()

            # TODO: Send reset email
            logger.info(f"Password reset token for {user.email}: {reset_token}")

        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except Exception as e:
        logger.error(f"Password reset request error: {str(e)}")
        # Don't reveal errors
        return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reset-password/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_password_reset(request: ResetPasswordConfirmRequest, req: Request):
    """Confirm password reset with token"""
    try:
        # Find user by reset token
        user = await User.find_one(User.reset_token == request.token)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )

        # Verify token
        if not user.verify_reset_token(request.token):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )

        # Validate new password
        is_valid, error_msg = auth_service.validate_password_strength(request.new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # Update password
        user.password_hash = auth_service.hash_password(request.new_password)
        user.clear_reset_token()
        await user.save()

        # Save to password history
        client_info = get_client_info(req)
        await PasswordHistory(
            user_id=str(user.id),
            password_hash=user.password_hash,
            changed_by_ip=client_info['ip_address']
        ).insert()

        # Revoke all refresh tokens
        await RefreshToken.revoke_all_user_tokens(str(user.id), "Password reset")

        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset confirmation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )
