"""
Authentication Service
Handles JWT token generation, validation, and user authentication
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
import bcrypt
import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Request
import logging
from functools import wraps
import re

logger = logging.getLogger(__name__)

class AuthService:
    """JWT-based authentication service"""

    def __init__(self):
        self.secret_key = os.getenv('JWT_SECRET_KEY', secrets.token_urlsafe(32))
        self.algorithm = 'HS256'
        self.access_token_expire = timedelta(minutes=30)
        self.refresh_token_expire = timedelta(days=7)
        self.security = HTTPBearer()

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )

    def create_access_token(self, user_id: str, email: str) -> str:
        """Create JWT access token"""
        expire = datetime.now(timezone.utc) + self.access_token_expire
        payload = {
            'sub': user_id,
            'email': email,
            'exp': expire,
            'iat': datetime.now(timezone.utc),
            'type': 'access'
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        """Create JWT refresh token"""
        expire = datetime.now(timezone.utc) + self.refresh_token_expire
        payload = {
            'sub': user_id,
            'exp': expire,
            'iat': datetime.now(timezone.utc),
            'type': 'refresh',
            'jti': secrets.token_urlsafe(32)  # Unique token ID
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )

    def validate_access_token(self, token: str) -> Dict[str, Any]:
        """Validate access token and return payload"""
        payload = self.decode_token(token)

        if payload.get('type') != 'access':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        return payload

    def validate_refresh_token(self, token: str) -> Dict[str, Any]:
        """Validate refresh token and return payload"""
        payload = self.decode_token(token)

        if payload.get('type') != 'refresh':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        return payload

    def extract_token(self, authorization: str) -> str:
        """Extract token from Authorization header"""
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header missing"
            )

        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format"
            )

        return parts[1]

    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """
        Validate password strength
        Returns: (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"

        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"

        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"

        if not re.search(r'\d', password):
            return False, "Password must contain at least one number"

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"

        return True, ""

    def create_token_pair(self, user_id: str, email: str) -> Dict[str, str]:
        """Create access and refresh token pair"""
        return {
            'access_token': self.create_access_token(user_id, email),
            'refresh_token': self.create_refresh_token(user_id),
            'token_type': 'bearer'
        }

    async def get_current_user_id(self, request: Request) -> str:
        """Extract user ID from request"""
        authorization = request.headers.get('Authorization', '')
        token = self.extract_token(authorization)
        payload = self.validate_access_token(token)
        return payload['sub']

# Singleton instance
auth_service = AuthService()