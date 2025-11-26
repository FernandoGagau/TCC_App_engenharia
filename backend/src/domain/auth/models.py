"""Authentication domain models."""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import uuid4

from beanie import Document, Indexed
from pydantic import BaseModel, Field, EmailStr


class UserRole(str, Enum):
    """User role types."""
    USER = "user"
    ADMIN = "admin"
    MANAGER = "manager"


class User(Document):
    """User document model."""

    user_id: Indexed(str) = Field(default_factory=lambda: str(uuid4()))
    email: Indexed(EmailStr, unique=True)
    username: Indexed(str, unique=True)
    password_hash: str
    full_name: Optional[str] = None
    roles: List[UserRole] = Field(default_factory=lambda: [UserRole.USER])

    # Account status
    is_active: bool = True
    is_verified: bool = False
    email_verified: bool = False

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

    # Security
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    two_factor_enabled: bool = False
    two_factor_secret: Optional[str] = None

    # Profile
    avatar_url: Optional[str] = None
    preferences: Dict = Field(default_factory=dict)

    class Settings:
        name = "users"
        indexes = [
            "email",
            "username",
            "user_id",
            [("email", 1), ("is_active", 1)]
        ]

    def update_last_login(self):
        """Update last login timestamp."""
        self.last_login = datetime.utcnow()
        self.failed_login_attempts = 0
        self.locked_until = None

    def increment_failed_login(self):
        """Increment failed login attempts."""
        self.failed_login_attempts += 1
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.locked_until = datetime.utcnow() + timedelta(minutes=30)

    def is_locked(self) -> bool:
        """Check if account is locked."""
        if self.locked_until:
            return datetime.utcnow() < self.locked_until
        return False

    def has_role(self, role: UserRole) -> bool:
        """Check if user has specific role."""
        return role in self.roles

    def to_dict(self) -> dict:
        """Convert to dictionary excluding sensitive data."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "roles": self.roles,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat(),
            "avatar_url": self.avatar_url
        }


class RefreshToken(Document):
    """Refresh token document model."""

    token_id: Indexed(str) = Field(default_factory=lambda: str(uuid4()))
    user_id: Indexed(str)
    token_hash: str
    expires_at: Indexed(datetime)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Token metadata
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Token status
    revoked: bool = False
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None

    # Token usage
    used_count: int = 0
    last_used: Optional[datetime] = None

    class Settings:
        name = "refresh_tokens"
        indexes = [
            "token_id",
            "user_id",
            "expires_at",
            [("user_id", 1), ("revoked", 1)],
            [("expires_at", 1), ("revoked", 1)]
        ]

    def revoke(self, reason: Optional[str] = None):
        """Revoke the token."""
        self.revoked = True
        self.revoked_at = datetime.utcnow()
        self.revoked_reason = reason

    def is_valid(self) -> bool:
        """Check if token is valid."""
        if self.revoked:
            return False
        if datetime.utcnow() >= self.expires_at:
            return False
        return True

    def update_usage(self):
        """Update token usage statistics."""
        self.used_count += 1
        self.last_used = datetime.utcnow()


class LoginAttempt(Document):
    """Login attempt tracking for security."""

    attempt_id: str = Field(default_factory=lambda: str(uuid4()))
    email: Optional[str] = None
    username: Optional[str] = None
    ip_address: str
    user_agent: Optional[str] = None

    # Attempt result
    success: bool
    failure_reason: Optional[str] = None

    # Timestamps
    attempted_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "login_attempts"
        indexes = [
            "email",
            "username",
            "ip_address",
            [("ip_address", 1), ("attempted_at", -1)],
            [("email", 1), ("attempted_at", -1)]
        ]


class PasswordResetToken(Document):
    """Password reset token model."""

    token_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: Indexed(str)
    token_hash: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Token status
    used: bool = False
    used_at: Optional[datetime] = None

    class Settings:
        name = "password_reset_tokens"
        indexes = [
            "user_id",
            "expires_at",
            [("user_id", 1), ("used", 1)]
        ]

    def is_valid(self) -> bool:
        """Check if token is valid."""
        if self.used:
            return False
        if datetime.utcnow() >= self.expires_at:
            return False
        return True

    def mark_used(self):
        """Mark token as used."""
        self.used = True
        self.used_at = datetime.utcnow()


from datetime import timedelta  # Add this import at the top