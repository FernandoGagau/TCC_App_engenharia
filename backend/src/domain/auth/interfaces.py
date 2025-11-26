"""
Authentication Domain Interfaces
Following SOLID principles for clean architecture
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class UserRepository(ABC):
    """Interface for user data access"""

    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find user by email"""
        pass

    @abstractmethod
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new user"""
        pass


class PasswordService(ABC):
    """Interface for password operations"""

    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Hash a password"""
        pass

    @abstractmethod
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        pass


class TokenService(ABC):
    """Interface for token operations"""

    @abstractmethod
    def create_access_token(self, user_id: str, email: str) -> str:
        """Create access token"""
        pass

    @abstractmethod
    def create_refresh_token(self, user_id: str, email: str) -> str:
        """Create refresh token"""
        pass

    @abstractmethod
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate and decode token"""
        pass


class AuthenticationService(ABC):
    """Interface for authentication business logic"""

    @abstractmethod
    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with email and password"""
        pass

    @abstractmethod
    async def create_user(self, email: str, password: str, full_name: str, username: str) -> Dict[str, Any]:
        """Create new user account"""
        pass