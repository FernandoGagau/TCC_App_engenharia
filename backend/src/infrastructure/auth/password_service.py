"""Password hashing and verification service."""

from passlib.context import CryptContext
from loguru import logger


class PasswordService:
    """Service for password hashing and verification."""

    def __init__(self):
        """Initialize password service."""
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12  # Cost factor for bcrypt
        )

    def hash_password(self, password: str) -> str:
        """Hash a plain password.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password to verify against

        Returns:
            True if password matches, False otherwise
        """
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    def needs_rehash(self, hashed_password: str) -> bool:
        """Check if password hash needs to be updated.

        Args:
            hashed_password: Existing password hash

        Returns:
            True if hash should be updated
        """
        return self.pwd_context.needs_update(hashed_password)

    def validate_password_strength(self, password: str) -> tuple[bool, str]:
        """Validate password strength.

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"

        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"

        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"

        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"

        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            return False, "Password must contain at least one special character"

        return True, ""


# Create singleton instance
password_service = PasswordService()