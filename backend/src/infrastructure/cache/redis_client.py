"""Resilient Redis client with production configuration."""

import asyncio
import ssl
import os
from typing import Optional, Any, Dict, List, Tuple
from urllib.parse import urlparse
from loguru import logger
import redis.asyncio as redis
from redis.asyncio import ConnectionPool
from redis.sentinel import Sentinel
from redis.backoff import ExponentialBackoff
from redis.retry import Retry
from redis.exceptions import RedisError, ConnectionError, TimeoutError


class RedisConfig:
    """Redis configuration settings."""

    def __init__(self, **kwargs):
        # Connection settings
        self.host = kwargs.get("host", "localhost")
        self.port = kwargs.get("port", 6379)
        self.password = kwargs.get("password", None)
        self.db = kwargs.get("db", 0)

        # Pool settings
        self.max_connections = kwargs.get("max_connections", 50)
        self.timeout = kwargs.get("timeout", 5)
        self.socket_timeout = kwargs.get("socket_timeout", 5)
        self.retry_on_timeout = kwargs.get("retry_on_timeout", True)
        self.health_check_interval = kwargs.get("health_check_interval", 30)

        # SSL settings
        self.ssl = kwargs.get("ssl", False)
        self.ssl_cert_path = kwargs.get("ssl_cert_path", None)
        self.ssl_cert_reqs = kwargs.get("ssl_cert_reqs", "required")

        # Sentinel settings
        self.use_sentinel = kwargs.get("use_sentinel", False)
        self.sentinels = kwargs.get("sentinels", [])
        self.master_name = kwargs.get("master_name", "mymaster")
        self.sentinel_password = kwargs.get("sentinel_password", None)

        # Retry settings
        self.max_retries = kwargs.get("max_retries", 3)
        self.retry_backoff_base = kwargs.get("retry_backoff_base", 0.1)
        self.retry_backoff_max = kwargs.get("retry_backoff_max", 30)


class ResilientRedisClient:
    """Production-ready Redis client with high availability."""

    def __init__(self, config: RedisConfig):
        self.config = config
        self.client: Optional[redis.Redis] = None
        self.sentinel: Optional[Sentinel] = None
        self.pool: Optional[ConnectionPool] = None
        self._connected = False
        self._reconnect_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """Connect to Redis with Sentinel support and auto-reconnect."""
        try:
            if self.config.use_sentinel:
                await self._connect_with_sentinel()
            else:
                await self._connect_direct()

            # Test connection
            await self.client.ping()
            self._connected = True
            logger.info("Redis connection established")

            # Start health check task
            self._start_health_check()

        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self._connected = False
            # Start reconnection task
            self._start_reconnect()
            raise

    async def _connect_with_sentinel(self) -> None:
        """Connect using Redis Sentinel for high availability."""
        # Create sentinel connection
        sentinels = [
            (host, port)
            for host, port in self.config.sentinels
        ]

        self.sentinel = Sentinel(
            sentinels,
            socket_connect_timeout=self.config.timeout,
            password=self.config.password,
            sentinel_kwargs={
                "password": self.config.sentinel_password
            } if self.config.sentinel_password else {}
        )

        # Get master from sentinel
        self.client = self.sentinel.master_for(
            self.config.master_name,
            socket_timeout=self.config.socket_timeout,
            connection_pool_class=redis.BlockingConnectionPool,
            max_connections=self.config.max_connections,
            retry_on_timeout=self.config.retry_on_timeout,
            retry=Retry(
                ExponentialBackoff(
                    base=self.config.retry_backoff_base,
                    cap=self.config.retry_backoff_max
                ),
                retries=self.config.max_retries
            ),
            decode_responses=True
        )

    async def _connect_direct(self) -> None:
        """Direct connection with connection pooling."""
        # Configure SSL if enabled
        ssl_config = None
        if self.config.ssl:
            ssl_config = ssl.create_default_context()
            if self.config.ssl_cert_reqs == "none":
                ssl_config.check_hostname = False
                ssl_config.verify_mode = ssl.CERT_NONE
            elif self.config.ssl_cert_path:
                ssl_config.load_verify_locations(self.config.ssl_cert_path)

        # Create connection pool
        self.pool = ConnectionPool(
            host=self.config.host,
            port=self.config.port,
            password=self.config.password,
            db=self.config.db,
            max_connections=self.config.max_connections,
            socket_connect_timeout=self.config.timeout,
            socket_timeout=self.config.socket_timeout,
            retry_on_timeout=self.config.retry_on_timeout,
            health_check_interval=self.config.health_check_interval,
            ssl=ssl_config is not None,
            ssl_context=ssl_config,
            decode_responses=True
        )

        # Create Redis client
        self.client = redis.Redis(
            connection_pool=self.pool,
            decode_responses=True
        )

    def _start_reconnect(self) -> None:
        """Start background reconnection task."""
        if self._reconnect_task is None or self._reconnect_task.done():
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """Background task to reconnect on connection loss."""
        backoff = 1
        while not self._connected:
            try:
                await asyncio.sleep(backoff)
                await self.connect()
                logger.info("Redis reconnection successful")
                break
            except Exception as e:
                logger.warning(f"Redis reconnection failed: {e}")
                backoff = min(backoff * 2, 60)  # Max 60 seconds

    def _start_health_check(self) -> None:
        """Start background health check task."""
        asyncio.create_task(self._health_check_loop())

    async def _health_check_loop(self) -> None:
        """Periodic health check."""
        while self._connected:
            await asyncio.sleep(30)  # Check every 30 seconds
            try:
                await self.client.ping()
            except Exception as e:
                logger.error(f"Redis health check failed: {e}")
                self._connected = False
                self._start_reconnect()

    async def get_with_fallback(
        self,
        key: str,
        fallback_fn=None,
        ttl: Optional[int] = None
    ) -> Optional[Any]:
        """Get value with fallback on failure."""
        try:
            value = await self.client.get(key)
            if value is None and fallback_fn:
                value = await fallback_fn() if asyncio.iscoroutinefunction(fallback_fn) else fallback_fn()
                if value is not None:
                    await self.set_with_retry(key, value, ex=ttl)
            return value
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis get error: {e}")
            if fallback_fn:
                return await fallback_fn() if asyncio.iscoroutinefunction(fallback_fn) else fallback_fn()
            return None

    async def set_with_retry(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
        retries: Optional[int] = None
    ) -> bool:
        """Set value with retry logic."""
        retries = retries or self.config.max_retries
        backoff = self.config.retry_backoff_base

        for attempt in range(retries):
            try:
                return await self.client.set(
                    key, value, ex=ex, px=px, nx=nx, xx=xx
                )
            except (ConnectionError, TimeoutError) as e:
                if attempt == retries - 1:
                    logger.error(f"Redis set failed after {retries} attempts: {e}")
                    return False
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.config.retry_backoff_max)
        return False

    async def delete_with_retry(
        self,
        *keys: str,
        retries: Optional[int] = None
    ) -> int:
        """Delete keys with retry logic."""
        retries = retries or self.config.max_retries
        backoff = self.config.retry_backoff_base

        for attempt in range(retries):
            try:
                return await self.client.delete(*keys)
            except (ConnectionError, TimeoutError) as e:
                if attempt == retries - 1:
                    logger.error(f"Redis delete failed after {retries} attempts: {e}")
                    return 0
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.config.retry_backoff_max)
        return 0

    async def pipeline_with_retry(self, commands: List[Tuple]) -> List[Any]:
        """Execute pipeline with retry logic."""
        retries = self.config.max_retries
        backoff = self.config.retry_backoff_base

        for attempt in range(retries):
            try:
                async with self.client.pipeline() as pipe:
                    for cmd in commands:
                        method = getattr(pipe, cmd[0])
                        method(*cmd[1:])
                    return await pipe.execute()
            except (ConnectionError, TimeoutError) as e:
                if attempt == retries - 1:
                    logger.error(f"Redis pipeline failed after {retries} attempts: {e}")
                    return []
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.config.retry_backoff_max)
        return []

    async def health_check(self) -> Dict[str, Any]:
        """Check Redis health status."""
        try:
            # Ping
            await self.client.ping()

            # Get info
            info = await self.client.info()

            # Parse relevant metrics
            return {
                "status": "healthy",
                "connected": self._connected,
                "connected_clients": info.get("connected_clients"),
                "used_memory": info.get("used_memory_human"),
                "used_memory_peak": info.get("used_memory_peak_human"),
                "used_memory_rss": info.get("used_memory_rss_human"),
                "mem_fragmentation_ratio": info.get("mem_fragmentation_ratio"),
                "uptime_seconds": info.get("uptime_in_seconds"),
                "role": info.get("role"),
                "connected_slaves": info.get("connected_slaves", 0),
                "total_connections_received": info.get("total_connections_received"),
                "total_commands_processed": info.get("total_commands_processed"),
                "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "evicted_keys": info.get("evicted_keys"),
                "expired_keys": info.get("expired_keys")
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": self._connected,
                "error": str(e)
            }

    async def get_slow_log(self, count: int = 10) -> List[Dict]:
        """Get slow query log."""
        try:
            slow_log = await self.client.slowlog_get(count)
            return [
                {
                    "id": entry[0],
                    "timestamp": entry[1],
                    "duration": entry[2],
                    "command": " ".join(entry[3])
                }
                for entry in slow_log
            ]
        except Exception as e:
            logger.error(f"Failed to get slow log: {e}")
            return []

    async def disconnect(self) -> None:
        """Gracefully disconnect from Redis."""
        self._connected = False

        # Cancel reconnection task if running
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()

        # Close connections
        if self.client:
            await self.client.close()

        if self.pool:
            await self.pool.disconnect()

        logger.info("Redis disconnected")


# Global instances
_redis_client: Optional[ResilientRedisClient] = None
redis_client: Optional[redis.Redis] = None  # Backwards compatibility


async def get_redis_client() -> Optional[redis.Redis]:
    """Get or create Redis client instance (backwards compatible)."""
    global _redis_client, redis_client

    if _redis_client and _redis_client.client:
        redis_client = _redis_client.client
        return redis_client

    if redis_client:
        return redis_client

    try:
        # Parse Redis URL from environment
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        parsed = urlparse(redis_url)

        # Check for sentinel configuration
        use_sentinel = os.getenv("REDIS_USE_SENTINEL", "false").lower() == "true"
        sentinels = []

        if use_sentinel:
            sentinel_hosts = os.getenv("REDIS_SENTINELS", "").split(",")
            for host in sentinel_hosts:
                if ":" in host:
                    h, p = host.split(":")
                    sentinels.append((h.strip(), int(p)))

        config = RedisConfig(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            password=parsed.password or os.getenv("REDIS_PASSWORD"),
            db=int(parsed.path[1:]) if parsed.path and len(parsed.path) > 1 else 0,
            max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "50")),
            timeout=int(os.getenv("REDIS_CONNECTION_TIMEOUT", "5")),
            socket_timeout=int(os.getenv("REDIS_SOCKET_TIMEOUT", "5")),
            retry_on_timeout=os.getenv("REDIS_RETRY_ON_TIMEOUT", "true").lower() == "true",
            ssl=os.getenv("REDIS_SSL", "false").lower() == "true",
            ssl_cert_path=os.getenv("REDIS_SSL_CERT_PATH"),
            ssl_cert_reqs=os.getenv("REDIS_SSL_CERT_REQS", "required"),
            use_sentinel=use_sentinel,
            sentinels=sentinels,
            master_name=os.getenv("REDIS_MASTER_NAME", "mymaster"),
            sentinel_password=os.getenv("REDIS_SENTINEL_PASSWORD")
        )

        _redis_client = ResilientRedisClient(config)
        await _redis_client.connect()
        redis_client = _redis_client.client
        return redis_client

    except Exception as e:
        logger.warning(f"Redis not available: {e}")
        return None


async def get_resilient_redis_client() -> Optional[ResilientRedisClient]:
    """Get resilient Redis client with advanced features."""
    global _redis_client

    if _redis_client:
        return _redis_client

    # This will create the client if not exists
    await get_redis_client()
    return _redis_client


async def close_redis():
    """Close Redis connection."""
    global _redis_client, redis_client

    if _redis_client:
        await _redis_client.disconnect()
        _redis_client = None

    if redis_client:
        await redis_client.close()
        redis_client = None

    logger.info("Redis connection closed")