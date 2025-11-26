"""
Simple Password Service Implementation
Single Responsibility: Handle password operations
"""

import hashlib
from domain.auth.interfaces import PasswordService


class SimplePasswordService(PasswordService):
    """Simple password service using SHA256"""

    def hash_password(self, password: str) -> str:
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return self.hash_password(password) == hashed