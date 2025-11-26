"""Authentication middleware and dependencies."""

from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from domain.auth.models import User, UserRole
from infrastructure.auth.jwt_service import jwt_service


# Security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """Get current user if authenticated (optional).

    Args:
        credentials: Bearer token credentials

    Returns:
        User if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        # Verify access token
        payload = jwt_service.verify_access_token(credentials.credentials)

        # Get user from database
        user_id = payload.get("sub")
        if not user_id:
            return None

        user = await User.find_one(User.user_id == user_id)
        if not user or not user.is_active:
            return None

        return user

    except HTTPException:
        return None
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current user (required).

    Args:
        credentials: Bearer token credentials

    Returns:
        Authenticated user

    Raises:
        HTTPException: If not authenticated
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        # Verify access token
        payload = jwt_service.verify_access_token(credentials.credentials)

        # Get user from database
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"}
            )

        user = await User.find_one(User.user_id == user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"}
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        if user.is_locked():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is locked"
            )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_verified_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current verified user.

    Args:
        current_user: Current authenticated user

    Returns:
        Verified user

    Raises:
        HTTPException: If user is not verified
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )

    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current admin user.

    Args:
        current_user: Current authenticated user

    Returns:
        Admin user

    Raises:
        HTTPException: If user is not admin
    """
    if not current_user.has_role(UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )

    return current_user


async def get_current_manager_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current manager or admin user.

    Args:
        current_user: Current authenticated user

    Returns:
        Manager or admin user

    Raises:
        HTTPException: If user is not manager or admin
    """
    if not (current_user.has_role(UserRole.MANAGER) or current_user.has_role(UserRole.ADMIN)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager privileges required"
        )

    return current_user


class RoleChecker:
    """Dependency for checking user roles."""

    def __init__(self, allowed_roles: list[UserRole]):
        """Initialize role checker.

        Args:
            allowed_roles: List of allowed roles
        """
        self.allowed_roles = allowed_roles

    async def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        """Check if user has required role.

        Args:
            current_user: Current authenticated user

        Returns:
            User if has required role

        Raises:
            HTTPException: If user doesn't have required role
        """
        for role in self.allowed_roles:
            if current_user.has_role(role):
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"One of these roles required: {', '.join(self.allowed_roles)}"
        )


# Convenience role checkers
require_admin = RoleChecker([UserRole.ADMIN])
require_manager = RoleChecker([UserRole.MANAGER, UserRole.ADMIN])
require_user = RoleChecker([UserRole.USER, UserRole.MANAGER, UserRole.ADMIN])


async def get_token_from_request(request: Request) -> Optional[str]:
    """Extract token from request (header or cookie).

    Args:
        request: FastAPI request

    Returns:
        Token string or None
    """
    # Try Authorization header first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "")

    # Try cookie
    return request.cookies.get("access_token")


async def verify_api_key(api_key: str = Depends(security)) -> bool:
    """Verify API key for service-to-service auth.

    Args:
        api_key: API key from header

    Returns:
        True if valid

    Raises:
        HTTPException: If API key is invalid
    """
    import os

    expected_api_key = os.getenv("INTERNAL_API_KEY")
    if not expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key not configured"
        )

    if api_key != expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return True