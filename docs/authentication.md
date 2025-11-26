# Authentication Documentation

This document provides comprehensive documentation for the authentication and authorization system in the Construction Analysis AI platform.

## Authentication Overview

### Current Status
The application currently operates **without authentication** for development purposes. This document outlines the planned authentication system for production deployment.

### Planned Authentication Strategy
- **Method**: JWT (JSON Web Tokens) with refresh token mechanism
- **Storage**: Secure HTTP-only cookies for web, secure storage for mobile
- **Session Management**: Redis-based session store (optional)
- **Authorization**: Role-Based Access Control (RBAC)

## Architecture Design

### Authentication Flow
```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   Client    │    │   Backend    │    │  Database   │
│  (React)    │    │  (FastAPI)   │    │ (MongoDB)   │
└─────┬───────┘    └──────┬───────┘    └─────┬───────┘
      │                   │                  │
      │ 1. Login Request  │                  │
      ├──────────────────►│                  │
      │                   │ 2. Verify Creds │
      │                   ├─────────────────►│
      │                   │ 3. User Data     │
      │                   │◄─────────────────┤
      │ 4. JWT + Refresh  │                  │
      │◄──────────────────┤                  │
      │                   │                  │
      │ 5. API Request    │                  │
      │   (with JWT)      │                  │
      ├──────────────────►│                  │
      │                   │ 6. Validate JWT │
      │                   │                  │
      │ 7. Response       │                  │
      │◄──────────────────┤                  │
```

### JWT Token Structure
```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user_id",
    "email": "user@example.com",
    "roles": ["user", "project_manager"],
    "permissions": ["read:projects", "write:projects"],
    "exp": 1640995200,
    "iat": 1640908800,
    "jti": "token_id"
  }
}
```

## User Model and Roles

### User Entity
```python
# src/domain/entities/user.py
from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, EmailStr
from passlib.context import CryptContext

class UserRole(str, Enum):
    ADMIN = "admin"
    PROJECT_MANAGER = "project_manager"
    ENGINEER = "engineer"
    USER = "user"
    VIEWER = "viewer"

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"

class User(BaseModel):
    """User entity for authentication and authorization."""

    id: Optional[str] = Field(None, alias="_id")
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=1, max_length=100)

    # Authentication
    password_hash: str = Field(..., description="Hashed password")
    is_email_verified: bool = False
    email_verification_token: Optional[str] = None

    # Authorization
    roles: List[UserRole] = Field(default_factory=lambda: [UserRole.USER])
    permissions: List[str] = Field(default_factory=list)
    status: UserStatus = UserStatus.PENDING_VERIFICATION

    # Profile
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    department: Optional[str] = None

    # Project associations
    project_ids: List[str] = Field(default_factory=list)
    default_project_id: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    last_activity: Optional[datetime] = None

    # Security
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    password_changed_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}

    def has_role(self, role: UserRole) -> bool:
        """Check if user has specific role."""
        return role in self.roles

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions

    def is_active(self) -> bool:
        """Check if user is active and not locked."""
        return (
            self.status == UserStatus.ACTIVE and
            (self.locked_until is None or self.locked_until < datetime.utcnow())
        )

    def can_access_project(self, project_id: str) -> bool:
        """Check if user can access specific project."""
        return (
            self.has_role(UserRole.ADMIN) or
            project_id in self.project_ids
        )
```

### Role-Based Permissions
```python
# src/domain/entities/permissions.py
from enum import Enum
from typing import Dict, List

class Permission(str, Enum):
    # Project permissions
    READ_PROJECTS = "read:projects"
    WRITE_PROJECTS = "write:projects"
    DELETE_PROJECTS = "delete:projects"
    MANAGE_PROJECTS = "manage:projects"

    # Analysis permissions
    READ_ANALYSES = "read:analyses"
    CREATE_ANALYSES = "create:analyses"
    DELETE_ANALYSES = "delete:analyses"

    # File permissions
    UPLOAD_FILES = "upload:files"
    DELETE_FILES = "delete:files"
    MANAGE_FILES = "manage:files"

    # User management
    READ_USERS = "read:users"
    WRITE_USERS = "write:users"
    DELETE_USERS = "delete:users"
    MANAGE_USERS = "manage:users"

    # System permissions
    VIEW_SYSTEM_LOGS = "view:system_logs"
    MANAGE_SYSTEM = "manage:system"

# Role-permission mapping
ROLE_PERMISSIONS: Dict[UserRole, List[Permission]] = {
    UserRole.VIEWER: [
        Permission.READ_PROJECTS,
        Permission.READ_ANALYSES,
    ],
    UserRole.USER: [
        Permission.READ_PROJECTS,
        Permission.READ_ANALYSES,
        Permission.CREATE_ANALYSES,
        Permission.UPLOAD_FILES,
    ],
    UserRole.ENGINEER: [
        Permission.READ_PROJECTS,
        Permission.WRITE_PROJECTS,
        Permission.READ_ANALYSES,
        Permission.CREATE_ANALYSES,
        Permission.DELETE_ANALYSES,
        Permission.UPLOAD_FILES,
        Permission.DELETE_FILES,
    ],
    UserRole.PROJECT_MANAGER: [
        Permission.READ_PROJECTS,
        Permission.WRITE_PROJECTS,
        Permission.DELETE_PROJECTS,
        Permission.MANAGE_PROJECTS,
        Permission.READ_ANALYSES,
        Permission.CREATE_ANALYSES,
        Permission.DELETE_ANALYSES,
        Permission.UPLOAD_FILES,
        Permission.DELETE_FILES,
        Permission.MANAGE_FILES,
        Permission.READ_USERS,
    ],
    UserRole.ADMIN: [
        # Admins have all permissions
        *Permission.__members__.values()
    ]
}

def get_permissions_for_role(role: UserRole) -> List[Permission]:
    """Get all permissions for a specific role."""
    return ROLE_PERMISSIONS.get(role, [])

def get_all_permissions_for_roles(roles: List[UserRole]) -> List[Permission]:
    """Get all permissions for multiple roles."""
    permissions = set()
    for role in roles:
        permissions.update(get_permissions_for_role(role))
    return list(permissions)
```

## Authentication Implementation

### Password Hashing
```python
# src/infrastructure/security/password.py
from passlib.context import CryptContext
from passlib.hash import bcrypt
import secrets
import string

class PasswordManager:
    """Handles password hashing and verification."""

    def __init__(self):
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12
        )

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)

    def generate_secure_password(self, length: int = 12) -> str:
        """Generate a secure random password."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def is_password_strong(self, password: str) -> tuple[bool, List[str]]:
        """Check if password meets security requirements."""
        issues = []

        if len(password) < 8:
            issues.append("Password must be at least 8 characters long")

        if not any(c.isupper() for c in password):
            issues.append("Password must contain at least one uppercase letter")

        if not any(c.islower() for c in password):
            issues.append("Password must contain at least one lowercase letter")

        if not any(c.isdigit() for c in password):
            issues.append("Password must contain at least one number")

        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            issues.append("Password must contain at least one special character")

        return len(issues) == 0, issues

password_manager = PasswordManager()
```

### JWT Token Management
```python
# src/infrastructure/security/jwt_manager.py
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from jwt.exceptions import InvalidTokenError

from ...domain.entities.user import User
from ..config.settings import settings

class JWTManager:
    """Handles JWT token creation and validation."""

    def __init__(self):
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.jwt_access_token_expire_minutes
        self.refresh_token_expire_days = settings.jwt_refresh_token_expire_days

    def create_access_token(self, user: User) -> str:
        """Create JWT access token for user."""
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.access_token_expire_minutes)

        payload = {
            "sub": user.id,
            "email": user.email,
            "username": user.username,
            "roles": [role.value for role in user.roles],
            "permissions": user.permissions,
            "iat": now,
            "exp": expire,
            "type": "access"
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token for user."""
        now = datetime.utcnow()
        expire = now + timedelta(days=self.refresh_token_expire_days)

        payload = {
            "sub": user.id,
            "iat": now,
            "exp": expire,
            "type": "refresh"
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except InvalidTokenError:
            return None

    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            exp = payload.get("exp")
            if exp:
                return datetime.utcnow() > datetime.fromtimestamp(exp)
            return True
        except InvalidTokenError:
            return True

jwt_manager = JWTManager()
```

### Authentication Service
```python
# src/application/services/auth_service.py
from datetime import datetime, timedelta
from typing import Optional, Tuple
import secrets

from ...domain.entities.user import User, UserStatus
from ...infrastructure.security.password import password_manager
from ...infrastructure.security.jwt_manager import jwt_manager
from ...infrastructure.database.repositories.user_repository import UserRepository

class AuthenticationError(Exception):
    """Base authentication error."""
    pass

class InvalidCredentialsError(AuthenticationError):
    """Invalid username/password."""
    pass

class AccountLockedError(AuthenticationError):
    """Account is locked due to failed attempts."""
    pass

class EmailNotVerifiedError(AuthenticationError):
    """Email address not verified."""
    pass

class AuthService:
    """Authentication service handling login, registration, etc."""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
        self.max_failed_attempts = 5
        self.lockout_duration_minutes = 30

    async def register_user(
        self,
        email: str,
        username: str,
        password: str,
        full_name: str
    ) -> User:
        """Register a new user."""
        # Check if user already exists
        existing_user = await self.user_repository.find_by_email(email)
        if existing_user:
            raise AuthenticationError("User with this email already exists")

        existing_username = await self.user_repository.find_by_username(username)
        if existing_username:
            raise AuthenticationError("Username already taken")

        # Validate password
        is_strong, issues = password_manager.is_password_strong(password)
        if not is_strong:
            raise AuthenticationError(f"Password requirements not met: {', '.join(issues)}")

        # Create user
        user = User(
            email=email,
            username=username,
            full_name=full_name,
            password_hash=password_manager.hash_password(password),
            email_verification_token=secrets.token_urlsafe(32),
            status=UserStatus.PENDING_VERIFICATION
        )

        # Save user
        saved_user = await self.user_repository.save(user)

        # TODO: Send verification email
        # await self.send_verification_email(saved_user)

        return saved_user

    async def authenticate_user(self, email: str, password: str) -> Tuple[str, str, User]:
        """Authenticate user and return tokens."""
        user = await self.user_repository.find_by_email(email)
        if not user:
            raise InvalidCredentialsError("Invalid email or password")

        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            raise AccountLockedError(f"Account locked until {user.locked_until}")

        # Check if email is verified
        if not user.is_email_verified:
            raise EmailNotVerifiedError("Please verify your email address")

        # Verify password
        if not password_manager.verify_password(password, user.password_hash):
            await self._handle_failed_login(user)
            raise InvalidCredentialsError("Invalid email or password")

        # Check if user is active
        if not user.is_active():
            raise AuthenticationError("Account is not active")

        # Reset failed attempts on successful login
        await self._handle_successful_login(user)

        # Generate tokens
        access_token = jwt_manager.create_access_token(user)
        refresh_token = jwt_manager.create_refresh_token(user)

        return access_token, refresh_token, user

    async def refresh_access_token(self, refresh_token: str) -> str:
        """Generate new access token using refresh token."""
        payload = jwt_manager.verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise AuthenticationError("Invalid refresh token")

        user_id = payload.get("sub")
        user = await self.user_repository.find_by_id(user_id)
        if not user or not user.is_active():
            raise AuthenticationError("User not found or inactive")

        return jwt_manager.create_access_token(user)

    async def verify_email(self, token: str) -> bool:
        """Verify user email with token."""
        user = await self.user_repository.find_by_verification_token(token)
        if not user:
            return False

        user.is_email_verified = True
        user.email_verification_token = None
        user.status = UserStatus.ACTIVE
        user.updated_at = datetime.utcnow()

        await self.user_repository.save(user)
        return True

    async def request_password_reset(self, email: str) -> bool:
        """Request password reset for user."""
        user = await self.user_repository.find_by_email(email)
        if not user:
            return False  # Don't reveal if email exists

        reset_token = secrets.token_urlsafe(32)
        reset_expires = datetime.utcnow() + timedelta(hours=1)

        user.password_reset_token = reset_token
        user.password_reset_expires = reset_expires
        user.updated_at = datetime.utcnow()

        await self.user_repository.save(user)

        # TODO: Send password reset email
        # await self.send_password_reset_email(user, reset_token)

        return True

    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password using reset token."""
        user = await self.user_repository.find_by_reset_token(token)
        if not user or user.password_reset_expires < datetime.utcnow():
            return False

        # Validate new password
        is_strong, issues = password_manager.is_password_strong(new_password)
        if not is_strong:
            raise AuthenticationError(f"Password requirements not met: {', '.join(issues)}")

        user.password_hash = password_manager.hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_expires = None
        user.password_changed_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()

        await self.user_repository.save(user)
        return True

    async def _handle_failed_login(self, user: User):
        """Handle failed login attempt."""
        user.failed_login_attempts += 1
        user.updated_at = datetime.utcnow()

        if user.failed_login_attempts >= self.max_failed_attempts:
            user.locked_until = datetime.utcnow() + timedelta(minutes=self.lockout_duration_minutes)

        await self.user_repository.save(user)

    async def _handle_successful_login(self, user: User):
        """Handle successful login."""
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        user.last_activity = datetime.utcnow()
        user.updated_at = datetime.utcnow()

        await self.user_repository.save(user)
```

## FastAPI Integration

### Authentication Dependencies
```python
# src/infrastructure/dependencies/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from ...domain.entities.user import User, Permission
from ...infrastructure.security.jwt_manager import jwt_manager
from ...infrastructure.database.repositories.user_repository import UserRepository
from ...infrastructure.dependencies.database import get_user_repository

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user_repository: UserRepository = Depends(get_user_repository)
) -> User:
    """Get current authenticated user."""
    token = credentials.credentials
    payload = jwt_manager.verify_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    user = await user_repository.find_by_id(user_id)

    if not user or not user.is_active():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    if not current_user.is_active():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

def require_permission(permission: Permission):
    """Decorator to require specific permission."""
    def permission_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not current_user.has_permission(permission.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission.value}"
            )
        return current_user
    return permission_checker

def require_role(role: UserRole):
    """Decorator to require specific role."""
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not current_user.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role.value}"
            )
        return current_user
    return role_checker

def require_project_access(project_id: str):
    """Decorator to require project access."""
    def project_access_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not current_user.can_access_project(project_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        return current_user
    return project_access_checker
```

### Authentication Endpoints
```python
# src/presentation/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from ....application.services.auth_service import AuthService, AuthenticationError
from ....infrastructure.dependencies.auth import get_current_user
from ....infrastructure.dependencies.services import get_auth_service

router = APIRouter(prefix="/auth", tags=["authentication"])

class UserRegistration(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegistration,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Register a new user."""
    try:
        user = await auth_service.register_user(
            email=user_data.email,
            username=user_data.username,
            password=user_data.password,
            full_name=user_data.full_name
        )
        return {"message": "User registered successfully. Please verify your email."}
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=TokenResponse)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Authenticate user and return tokens."""
    try:
        access_token, refresh_token, user = await auth_service.authenticate_user(
            email=form_data.username,  # Using username field for email
            password=form_data.password
        )

        # Set refresh token as HTTP-only cookie
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=30 * 24 * 60 * 60  # 30 days
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=30 * 60  # 30 minutes
        )

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh access token."""
    try:
        access_token = await auth_service.refresh_access_token(token_data.refresh_token)
        return TokenResponse(
            access_token=access_token,
            refresh_token=token_data.refresh_token,
            expires_in=30 * 60
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@router.post("/logout")
async def logout(response: Response):
    """Logout user by clearing cookies."""
    response.delete_cookie("refresh_token")
    return {"message": "Successfully logged out"}

@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "roles": current_user.roles,
        "permissions": current_user.permissions,
        "last_login": current_user.last_login
    }

@router.post("/verify-email/{token}")
async def verify_email(
    token: str,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Verify user email address."""
    success = await auth_service.verify_email(token)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    return {"message": "Email verified successfully"}
```

### Protected Route Example
```python
# Example of protected routes with different permission levels

@router.get("/projects", dependencies=[Depends(require_permission(Permission.READ_PROJECTS))])
async def list_projects():
    """List projects - requires READ_PROJECTS permission."""
    pass

@router.post("/projects", dependencies=[Depends(require_permission(Permission.WRITE_PROJECTS))])
async def create_project():
    """Create project - requires WRITE_PROJECTS permission."""
    pass

@router.delete("/projects/{project_id}", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def delete_project(project_id: str):
    """Delete project - requires ADMIN role."""
    pass

@router.get("/projects/{project_id}/analysis")
async def get_project_analysis(
    project_id: str,
    current_user: User = Depends(require_project_access(project_id))
):
    """Get project analysis - requires project access."""
    pass
```

## Frontend Integration

### Authentication Context
```javascript
// frontend/src/contexts/AuthContext.js
import React, { createContext, useContext, useReducer, useEffect } from 'react';

const AuthContext = createContext();

const authReducer = (state, action) => {
  switch (action.type) {
    case 'LOGIN_SUCCESS':
      return {
        ...state,
        isAuthenticated: true,
        user: action.payload.user,
        token: action.payload.token,
        loading: false,
        error: null
      };
    case 'LOGIN_FAILURE':
      return {
        ...state,
        isAuthenticated: false,
        user: null,
        token: null,
        loading: false,
        error: action.payload
      };
    case 'LOGOUT':
      return {
        ...state,
        isAuthenticated: false,
        user: null,
        token: null,
        loading: false,
        error: null
      };
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    default:
      return state;
  }
};

export const AuthProvider = ({ children }) => {
  const [state, dispatch] = useReducer(authReducer, {
    isAuthenticated: false,
    user: null,
    token: null,
    loading: true,
    error: null
  });

  useEffect(() => {
    // Check for existing token on mount
    const token = localStorage.getItem('access_token');
    if (token) {
      // Verify token and get user info
      fetchUserInfo(token);
    } else {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, []);

  const login = async (email, password) => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });

      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username: email, password })
      });

      if (!response.ok) {
        throw new Error('Login failed');
      }

      const data = await response.json();

      localStorage.setItem('access_token', data.access_token);

      const userResponse = await fetch('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${data.access_token}` }
      });

      const user = await userResponse.json();

      dispatch({
        type: 'LOGIN_SUCCESS',
        payload: { user, token: data.access_token }
      });

    } catch (error) {
      dispatch({
        type: 'LOGIN_FAILURE',
        payload: error.message
      });
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    dispatch({ type: 'LOGOUT' });
  };

  const fetchUserInfo = async (token) => {
    try {
      const response = await fetch('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.ok) {
        const user = await response.json();
        dispatch({
          type: 'LOGIN_SUCCESS',
          payload: { user, token }
        });
      } else {
        logout();
      }
    } catch (error) {
      logout();
    }
  };

  return (
    <AuthContext.Provider value={{
      ...state,
      login,
      logout
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
```

### Protected Route Component
```javascript
// frontend/src/components/ProtectedRoute.js
import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const ProtectedRoute = ({ children, requiredRole, requiredPermission }) => {
  const { isAuthenticated, user, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (requiredRole && !user.roles.includes(requiredRole)) {
    return <Navigate to="/unauthorized" replace />;
  }

  if (requiredPermission && !user.permissions.includes(requiredPermission)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return children;
};

export default ProtectedRoute;
```

This authentication documentation provides a comprehensive foundation for implementing secure user authentication and authorization in the Construction Analysis AI System, covering both backend JWT implementation and frontend React integration.