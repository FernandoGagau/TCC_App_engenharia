"""JWT service for token generation and validation."""

import os
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from jose import JWTError, jwt
from fastapi import HTTPException, status
from loguru import logger


class JWTService:
    """JWT service for authentication tokens."""

    def __init__(self):
        """Initialize JWT service."""
        self.secret_key = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
        self.refresh_secret_key = os.getenv("JWT_REFRESH_SECRET_KEY", secrets.token_urlsafe(32))
        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
        self.refresh_token_expire_days = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

        # Log warning if using default keys
        if "JWT_SECRET_KEY" not in os.environ:
            logger.warning("Using default JWT secret key. Set JWT_SECRET_KEY in production!")

    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create access token.

        Args:
            data: Token payload data
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()

        # Set expiration
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        # Add token metadata
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
            "jti": secrets.token_urlsafe(16)  # JWT ID for tracking
        })

        # Encode token
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create refresh token.

        Args:
            data: Token payload data
            expires_delta: Optional custom expiration time

        Returns:
            Encoded refresh token
        """
        to_encode = data.copy()

        # Set expiration
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)

        # Add token metadata
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": secrets.token_urlsafe(16)
        })

        # Encode token with refresh secret
        encoded_jwt = jwt.encode(to_encode, self.refresh_secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """Verify access token.

        Args:
            token: JWT token to verify

        Returns:
            Token payload

        Raises:
            HTTPException: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )

            # Verify token type
            if payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                    headers={"WWW-Authenticate": "Bearer"}
                )

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except JWTError as e:
            logger.error(f"JWT validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )

    def verify_refresh_token(self, token: str) -> Dict[str, Any]:
        """Verify refresh token.

        Args:
            token: Refresh token to verify

        Returns:
            Token payload

        Raises:
            HTTPException: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.refresh_secret_key,
                algorithms=[self.algorithm]
            )

            # Verify token type
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired"
            )
        except JWTError as e:
            logger.error(f"Refresh token validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

    def decode_token_unsafe(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode token without verification (for debugging).

        Args:
            token: JWT token

        Returns:
            Token payload or None

        Warning:
            This method does not verify the token signature.
            Use only for debugging or logging purposes.
        """
        try:
            return jwt.get_unverified_claims(token)
        except JWTError:
            return None

    def create_token_pair(self, user_data: Dict[str, Any]) -> Dict[str, str]:
        """Create access and refresh token pair.

        Args:
            user_data: User information to encode

        Returns:
            Dictionary with access_token and refresh_token
        """
        # Create access token with user data
        access_token = self.create_access_token(user_data)

        # Create refresh token with minimal data
        refresh_data = {
            "sub": user_data.get("sub"),  # User ID
            "email": user_data.get("email")
        }
        refresh_token = self.create_refresh_token(refresh_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    def get_token_expiry(self, token: str, token_type: str = "access") -> Optional[datetime]:
        """Get token expiration time.

        Args:
            token: JWT token
            token_type: Type of token (access or refresh)

        Returns:
            Expiration datetime or None
        """
        try:
            if token_type == "refresh":
                payload = jwt.decode(
                    token,
                    self.refresh_secret_key,
                    algorithms=[self.algorithm],
                    options={"verify_exp": False}
                )
            else:
                payload = jwt.decode(
                    token,
                    self.secret_key,
                    algorithms=[self.algorithm],
                    options={"verify_exp": False}
                )

            exp = payload.get("exp")
            if exp:
                return datetime.fromtimestamp(exp)

        except JWTError:
            pass

        return None


# Create singleton instance
jwt_service = JWTService()