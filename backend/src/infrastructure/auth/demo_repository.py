"""
Demo User Repository Implementation
Single Responsibility: Handle demo user data access
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
import hashlib

from domain.auth.interfaces import UserRepository


class DemoUserRepository(UserRepository):
    """In-memory repository for demo users"""

    def __init__(self):
        self._users = self._create_demo_users()

    def _create_demo_users(self) -> Dict[str, Dict[str, Any]]:
        """Create demo users with proper password hashes"""
        return {
            "demo@example.com": {
                "id": "demo-user-001",
                "email": "demo@example.com",
                "username": "demo",
                "full_name": "Demo User",
                "password_hash": self._hash_password("Demo@123"),
                "role": "user",
                "is_verified": True,
                "is_active": True,
                "avatar_url": None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
        }

    def _hash_password(self, password: str) -> str:
        """Simple SHA256 hash for demo purposes"""
        return hashlib.sha256(password.encode()).hexdigest()

    async def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find user by email"""
        return self._users.get(email.lower())

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new user (demo implementation)"""
        user_id = f"user-{int(datetime.now().timestamp())}"
        new_user = {
            "id": user_id,
            "email": user_data["email"],
            "username": user_data.get("username", "newuser"),
            "full_name": user_data.get("full_name", "New User"),
            "password_hash": user_data["password_hash"],
            "role": "user",
            "is_verified": True,
            "is_active": True,
            "avatar_url": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        self._users[user_data["email"]] = new_user
        return new_user