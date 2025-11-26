"""
Token Service Implementation
Single Responsibility: Handle JWT token operations
"""

import secrets
import time
from typing import Dict, Any, Optional
from domain.auth.interfaces import TokenService


class SimpleTokenService(TokenService):
    """Simple token service for demo purposes"""

    def create_access_token(self, user_id: str, email: str) -> str:
        """Create access token"""
        timestamp = int(time.time())
        token = f"access_{secrets.token_urlsafe(32)}_{timestamp}"
        return token

    def create_refresh_token(self, user_id: str, email: str) -> str:
        """Create refresh token"""
        timestamp = int(time.time())
        token = f"refresh_{secrets.token_urlsafe(32)}_{timestamp}"
        return token

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate token (simplified for demo)"""
        if token and ("access_" in token or "refresh_" in token):
            return {
                "valid": True,
                "user_id": "demo-user-001",
                "email": "demo@example.com"
            }
        return None