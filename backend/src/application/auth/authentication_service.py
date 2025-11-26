"""
Authentication Service Implementation
Open/Closed Principle: Extensible without modification
Dependency Inversion: Depends on abstractions
"""

from typing import Dict, Any, Optional
from domain.auth.interfaces import (
    AuthenticationService,
    UserRepository,
    PasswordService,
    TokenService
)


class DemoAuthenticationService(AuthenticationService):
    """Authentication service implementation for demo environment"""

    def __init__(
        self,
        user_repository: UserRepository,
        password_service: PasswordService,
        token_service: TokenService
    ):
        self._user_repo = user_repository
        self._password_service = password_service
        self._token_service = token_service

    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with email and password"""
        # Find user
        user = await self._user_repo.find_by_email(email)
        if not user:
            return None

        # Verify password
        if not self._password_service.verify_password(password, user["password_hash"]):
            return None

        # Check if user is active
        if not user.get("is_active", True):
            return None

        return user

    async def create_user(self, email: str, password: str, full_name: str, username: str) -> Dict[str, Any]:
        """Create new user account"""
        # Hash password
        password_hash = self._password_service.hash_password(password)

        # Create user data
        user_data = {
            "email": email,
            "password_hash": password_hash,
            "full_name": full_name,
            "username": username
        }

        # Save user
        return await self._user_repo.create_user(user_data)

    def create_auth_tokens(self, user: Dict[str, Any]) -> Dict[str, str]:
        """Create authentication tokens for user"""
        access_token = self._token_service.create_access_token(user["id"], user["email"])
        refresh_token = self._token_service.create_refresh_token(user["id"], user["email"])

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }