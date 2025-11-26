"""
MongoDB models for authentication
Includes User and RefreshToken models
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import Field, EmailStr, validator
from beanie import Document, Indexed, before_event, Replace, Insert
import secrets

class User(Document):
    """User model for authentication"""

    # Basic information
    email: Indexed(EmailStr, unique=True)
    username: Indexed(str, unique=True)
    full_name: str
    password_hash: str

    # Profile information
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    company: Optional[str] = None
    role: str = "user"  # user, admin, moderator

    # Account status
    is_active: bool = True
    is_verified: bool = False
    verification_token: Optional[str] = None
    verification_sent_at: Optional[datetime] = None

    # Password reset
    reset_token: Optional[str] = None
    reset_token_expires: Optional[datetime] = None
    reset_requested_at: Optional[datetime] = None

    # Security
    last_login: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None

    # Preferences
    preferences: Dict[str, Any] = Field(default_factory=dict)
    notifications_enabled: bool = True
    email_notifications: bool = True

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Soft delete
    deleted_at: Optional[datetime] = None
    is_deleted: bool = False

    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if len(v) > 30:
            raise ValueError('Username must be less than 30 characters')
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, underscores and dashes')
        return v.lower()

    @validator('full_name')
    def validate_full_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Full name must be at least 2 characters')
        if len(v) > 100:
            raise ValueError('Full name must be less than 100 characters')
        return v.strip()

    @before_event([Replace, Insert])
    async def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    def is_locked(self) -> bool:
        """Check if account is locked"""
        if self.locked_until:
            if datetime.now(timezone.utc) < self.locked_until:
                return True
            else:
                # Lock expired, reset
                self.locked_until = None
                self.failed_login_attempts = 0
        return False

    def record_failed_login(self):
        """Record a failed login attempt"""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            # Lock account for 15 minutes
            from datetime import timedelta
            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)

    def record_successful_login(self, ip_address: str = None):
        """Record a successful login"""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login = datetime.now(timezone.utc)
        if ip_address:
            self.last_login_ip = ip_address

    def generate_verification_token(self) -> str:
        """Generate email verification token"""
        self.verification_token = secrets.token_urlsafe(32)
        self.verification_sent_at = datetime.now(timezone.utc)
        return self.verification_token

    def generate_reset_token(self) -> str:
        """Generate password reset token"""
        from datetime import timedelta
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        self.reset_requested_at = datetime.now(timezone.utc)
        return self.reset_token

    def verify_reset_token(self, token: str) -> bool:
        """Verify password reset token"""
        if not self.reset_token or self.reset_token != token:
            return False
        if not self.reset_token_expires:
            return False
        if datetime.now(timezone.utc) > self.reset_token_expires:
            return False
        return True

    def clear_reset_token(self):
        """Clear reset token after use"""
        self.reset_token = None
        self.reset_token_expires = None
        self.reset_requested_at = None

    def soft_delete(self):
        """Soft delete user"""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    class Settings:
        name = "users"
        indexes = [
            [("email", 1)],
            [("username", 1)],
            [("is_active", 1), ("is_deleted", 1)],
            [("created_at", -1)],
            [("verification_token", 1)],
            [("reset_token", 1)]
        ]


class RefreshToken(Document):
    """Refresh token model for JWT authentication"""

    # Token information
    token_id: Indexed(str, unique=True)  # jti from JWT
    user_id: Indexed(str)
    token_hash: str  # Hashed version of the token

    # Device/session information
    device_name: Optional[str] = None
    device_type: Optional[str] = None  # mobile, desktop, tablet
    browser: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Token lifecycle
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    last_used: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    use_count: int = 0

    # Security
    is_revoked: bool = False
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None

    @before_event([Replace, Insert])
    async def update_last_used(self):
        self.last_used = datetime.now(timezone.utc)
        self.use_count += 1

    def is_expired(self) -> bool:
        """Check if token is expired"""
        # Make expires_at timezone aware if it isn't already
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expires_at

    def is_valid(self) -> bool:
        """Check if token is valid (not expired or revoked)"""
        return not self.is_expired() and not self.is_revoked

    def revoke(self, reason: str = None):
        """Revoke the token"""
        self.is_revoked = True
        self.revoked_at = datetime.now(timezone.utc)
        if reason:
            self.revoked_reason = reason

    @classmethod
    async def revoke_all_user_tokens(cls, user_id: str, reason: str = "User logout"):
        """Revoke all tokens for a user"""
        await cls.find(
            cls.user_id == user_id,
            cls.is_revoked == False
        ).update_many(
            {"$set": {
                "is_revoked": True,
                "revoked_at": datetime.now(timezone.utc),
                "revoked_reason": reason
            }}
        )

    @classmethod
    async def cleanup_expired(cls):
        """Remove expired tokens"""
        cutoff = datetime.now(timezone.utc)
        await cls.find(cls.expires_at < cutoff).delete()

    class Settings:
        name = "refresh_tokens"
        indexes = [
            [("token_id", 1)],
            [("user_id", 1), ("is_revoked", 1)],
            [("expires_at", 1)],
            [("issued_at", -1)]
        ]


class LoginAttempt(Document):
    """Track login attempts for security monitoring"""

    email: str
    ip_address: str
    user_agent: Optional[str] = None
    success: bool
    failure_reason: Optional[str] = None
    attempted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Geolocation (optional)
    country: Optional[str] = None
    city: Optional[str] = None

    class Settings:
        name = "login_attempts"
        indexes = [
            [("email", 1), ("attempted_at", -1)],
            [("ip_address", 1), ("attempted_at", -1)],
            [("attempted_at", -1)]
        ]


class PasswordHistory(Document):
    """Track password history to prevent reuse"""

    user_id: Indexed(str)
    password_hash: str
    changed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    changed_by_ip: Optional[str] = None

    @classmethod
    async def check_password_reuse(cls, user_id: str, password_hash: str, limit: int = 5) -> bool:
        """Check if password was recently used"""
        recent_passwords = await cls.find(
            cls.user_id == user_id
        ).sort("-changed_at").limit(limit).to_list()

        return any(p.password_hash == password_hash for p in recent_passwords)

    class Settings:
        name = "password_history"
        indexes = [
            [("user_id", 1), ("changed_at", -1)]
        ]