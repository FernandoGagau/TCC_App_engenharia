"""Rate limiting implementation."""

from datetime import datetime, timedelta
from typing import Dict, Optional
from uuid import uuid4

import redis.asyncio as redis
from loguru import logger


class RateLimiter:
    """Rate limiter using Redis with sliding window algorithm."""

    def __init__(self, redis_client: redis.Redis):
        """Initialize rate limiter."""
        self.redis = redis_client

    async def check_rate_limit(
        self,
        user_id: str,
        limit: int = 30,
        window: int = 60
    ) -> bool:
        """Check if user has exceeded rate limit.

        Args:
            user_id: User identifier
            limit: Maximum number of requests allowed
            window: Time window in seconds

        Returns:
            True if within limit, False if exceeded
        """
        key = f"rate_limit:{user_id}"
        now = datetime.utcnow().timestamp()
        window_start = now - window

        try:
            # Remove old entries outside the window
            await self.redis.zremrangebyscore(key, 0, window_start)

            # Count current requests in window
            count = await self.redis.zcard(key)

            if count >= limit:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                return False

            # Add new request
            request_id = str(uuid4())
            await self.redis.zadd(key, {request_id: now})

            # Set expiry to clean up old keys
            await self.redis.expire(key, window)

            return True

        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # Allow on error to prevent blocking users
            return True

    async def get_remaining_quota(
        self,
        user_id: str,
        limit: int = 30,
        window: int = 60
    ) -> Dict[str, int]:
        """Get remaining quota for user.

        Args:
            user_id: User identifier
            limit: Maximum number of requests allowed
            window: Time window in seconds

        Returns:
            Dictionary with quota information
        """
        key = f"rate_limit:{user_id}"
        now = datetime.utcnow().timestamp()
        window_start = now - window

        try:
            # Remove old entries
            await self.redis.zremrangebyscore(key, 0, window_start)

            # Count current requests
            count = await self.redis.zcard(key)

            # Get TTL
            ttl = await self.redis.ttl(key)
            if ttl < 0:
                ttl = window

            return {
                "used": count,
                "limit": limit,
                "remaining": max(0, limit - count),
                "reset_in": ttl
            }

        except Exception as e:
            logger.error(f"Get quota error: {e}")
            return {
                "used": 0,
                "limit": limit,
                "remaining": limit,
                "reset_in": window
            }

    async def reset_limit(self, user_id: str) -> bool:
        """Reset rate limit for user.

        Args:
            user_id: User identifier

        Returns:
            True if successful
        """
        key = f"rate_limit:{user_id}"

        try:
            await self.redis.delete(key)
            logger.info(f"Rate limit reset for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Reset limit error: {e}")
            return False

    async def check_global_rate_limit(
        self,
        limit: int = 1000,
        window: int = 60
    ) -> bool:
        """Check global rate limit across all users.

        Args:
            limit: Maximum global requests allowed
            window: Time window in seconds

        Returns:
            True if within limit, False if exceeded
        """
        return await self.check_rate_limit(
            user_id="_global_",
            limit=limit,
            window=window
        )


class IPRateLimiter:
    """IP-based rate limiter."""

    def __init__(self, redis_client: redis.Redis):
        """Initialize IP rate limiter."""
        self.redis = redis_client

    async def check_ip_limit(
        self,
        ip_address: str,
        limit: int = 100,
        window: int = 60
    ) -> bool:
        """Check if IP has exceeded rate limit.

        Args:
            ip_address: IP address
            limit: Maximum requests allowed
            window: Time window in seconds

        Returns:
            True if within limit, False if exceeded
        """
        key = f"ip_limit:{ip_address}"
        now = datetime.utcnow().timestamp()
        window_start = now - window

        try:
            # Remove old entries
            await self.redis.zremrangebyscore(key, 0, window_start)

            # Count current requests
            count = await self.redis.zcard(key)

            if count >= limit:
                logger.warning(f"IP rate limit exceeded for {ip_address}")
                return False

            # Add new request
            request_id = str(uuid4())
            await self.redis.zadd(key, {request_id: now})

            # Set expiry
            await self.redis.expire(key, window)

            return True

        except Exception as e:
            logger.error(f"IP rate limit check error: {e}")
            return True

    async def ban_ip(
        self,
        ip_address: str,
        duration: int = 3600
    ) -> bool:
        """Temporarily ban an IP address.

        Args:
            ip_address: IP address to ban
            duration: Ban duration in seconds

        Returns:
            True if successful
        """
        key = f"ip_ban:{ip_address}"

        try:
            await self.redis.set(key, "1", ex=duration)
            logger.warning(f"IP {ip_address} banned for {duration} seconds")
            return True

        except Exception as e:
            logger.error(f"IP ban error: {e}")
            return False

    async def is_ip_banned(self, ip_address: str) -> bool:
        """Check if IP is banned.

        Args:
            ip_address: IP address to check

        Returns:
            True if banned, False otherwise
        """
        key = f"ip_ban:{ip_address}"

        try:
            result = await self.redis.get(key)
            return result is not None

        except Exception as e:
            logger.error(f"IP ban check error: {e}")
            return False


class MessageRateLimiter:
    """Message-specific rate limiter with different limits."""

    def __init__(self, redis_client: redis.Redis):
        """Initialize message rate limiter."""
        self.redis = redis_client
        self.limits = {
            "message": (30, 60),      # 30 messages per minute
            "stream": (10, 60),       # 10 streams per minute
            "attachment": (5, 60),    # 5 attachments per minute
            "reaction": (100, 60),    # 100 reactions per minute
        }

    async def check_message_limit(
        self,
        user_id: str,
        message_type: str = "message"
    ) -> bool:
        """Check rate limit for specific message type.

        Args:
            user_id: User identifier
            message_type: Type of message

        Returns:
            True if within limit, False if exceeded
        """
        if message_type not in self.limits:
            message_type = "message"

        limit, window = self.limits[message_type]
        key = f"msg_limit:{user_id}:{message_type}"
        now = datetime.utcnow().timestamp()
        window_start = now - window

        try:
            # Remove old entries
            await self.redis.zremrangebyscore(key, 0, window_start)

            # Count current requests
            count = await self.redis.zcard(key)

            if count >= limit:
                logger.warning(
                    f"Message rate limit exceeded for user {user_id}, "
                    f"type {message_type}"
                )
                return False

            # Add new request
            request_id = str(uuid4())
            await self.redis.zadd(key, {request_id: now})

            # Set expiry
            await self.redis.expire(key, window)

            return True

        except Exception as e:
            logger.error(f"Message rate limit check error: {e}")
            return True

    async def get_all_quotas(self, user_id: str) -> Dict[str, Dict[str, int]]:
        """Get all message type quotas for user.

        Args:
            user_id: User identifier

        Returns:
            Dictionary of quotas by message type
        """
        quotas = {}

        for message_type, (limit, window) in self.limits.items():
            key = f"msg_limit:{user_id}:{message_type}"
            now = datetime.utcnow().timestamp()
            window_start = now - window

            try:
                # Remove old entries
                await self.redis.zremrangebyscore(key, 0, window_start)

                # Count current requests
                count = await self.redis.zcard(key)

                # Get TTL
                ttl = await self.redis.ttl(key)
                if ttl < 0:
                    ttl = window

                quotas[message_type] = {
                    "used": count,
                    "limit": limit,
                    "remaining": max(0, limit - count),
                    "reset_in": ttl
                }

            except Exception as e:
                logger.error(f"Get quota error for {message_type}: {e}")
                quotas[message_type] = {
                    "used": 0,
                    "limit": limit,
                    "remaining": limit,
                    "reset_in": window
                }

        return quotas