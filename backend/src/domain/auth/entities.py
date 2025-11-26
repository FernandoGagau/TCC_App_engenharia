"""
Authentication Domain Entities
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class User(BaseModel):
    """User entity"""
    id: str
    email: EmailStr
    username: str
    full_name: str
    password_hash: str
    role: str = "user"
    is_verified: bool = True
    is_active: bool = True
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AuthCredentials(BaseModel):
    """Authentication credentials"""
    email: EmailStr
    password: str
    remember_me: bool = False


class AuthTokens(BaseModel):
    """Authentication tokens"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800


class AuthResponse(BaseModel):
    """Complete authentication response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800
    user: dict