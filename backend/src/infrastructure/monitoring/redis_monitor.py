"""Redis monitoring with Prometheus metrics."""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger

try:
    from prometheus_client import Gauge, Counter, Histogram, Summary
    PROMETHEUS_AVAILABLE = True
except ImportError:
    logger.warning("Prometheus client not installed. Metrics collection disabled.")
    PROMETHEUS_AVAILABLE = False


if PROMETHEUS_AVAILABLE:
    # Connection metrics
    redis_connections = Gauge(
        'redis_connections',
        'Number of active Redis connections'
    )

    redis_connection_pool_size = Gauge(
        'redis_connection_pool_size',
        'Size of the Redis connection pool'
    )

    redis_connection_pool_used = Gauge(
        'redis_connection_pool_used',
        'Number of connections currently in use'
    )

    # Memory metrics
    redis_memory_usage = Gauge(
        'redis_memory_usage_bytes',
        'Redis memory usage in bytes'
    )

    redis_memory_peak = Gauge(
        'redis_memory_peak_bytes',
        'Redis peak memory usage in bytes'
    )

    redis_memory_fragmentation = Gauge(
        'redis_memory_fragmentation_ratio',
        'Redis memory fragmentation ratio'
    )

    # Performance metrics
    redis_operations = Counter(
        'redis_operations_total',
        'Total Redis operations',
        ['operation', 'status']
    )

    redis_latency = Histogram(
        'redis_operation_duration_seconds',
        'Redis operation latency',
        ['operation'],
        buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
    )

    redis_slow_queries = Counter(
        'redis_slow_queries_total',
        'Total number of slow queries'
    )

    # Key metrics
    redis_keys_total = Gauge(
        'redis_keys_total',
        'Total number of keys in Redis',
        ['db']
    )

    redis_keys_expired = Counter(
        'redis_keys_expired_total',
        'Total number of expired keys'
    )

    redis_keys_evicted = Counter(
        'redis_keys_evicted_total',
        'Total number of evicted keys'
    )

    # Replication metrics
    redis_replication_lag = Gauge(
        'redis_replication_lag_seconds',
        'Redis replication lag in seconds'
    )

    redis_connected_slaves = Gauge(
        'redis_connected_slaves',
        'Number of connected Redis slaves'
    )

    # Error metrics
    redis_errors = Counter(
        'redis_errors_total',
        'Total Redis errors',
        ['error_type']
    )

    redis_reconnections = Counter(
        'redis_reconnections_total',
        'Total Redis reconnection attempts'
    )


class RedisMonitor:
    """Monitor Redis performance and health."""

    def __init__(self, redis_client):
        """Initialize Redis monitor.

        Args:
            redis_client: ResilientRedisClient instance
        """
        self.redis_client = redis_client
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._slow_query_threshold = 10000  # microseconds (10ms)

    async def start_monitoring(self, interval: int = 60):
        """Start monitoring Redis metrics.

        Args:
            interval: Collection interval in seconds
        """
        if not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus not available, monitoring disabled")
            return

        if self._monitoring:
            logger.warning("Monitoring already started")
            return

        self._monitoring = True
        self._monitor_task = asyncio.create_task(
            self._monitor_loop(interval)
        )
        logger.info(f"Redis monitoring started (interval: {interval}s)")

    async def stop_monitoring(self):
        """Stop monitoring Redis metrics."""
        self._monitoring = False

        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("Redis monitoring stopped")

    async def _monitor_loop(self, interval: int):
        """Main monitoring loop."""
        while self._monitoring:
            try:
                await self.collect_metrics()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error collecting Redis metrics: {e}")
                redis_errors.labels(error_type="monitoring").inc()
                await asyncio.sleep(interval)

    async def collect_metrics(self):
        """Collect all Redis metrics."""
        try:
            # Get Redis info
            info = await self.redis_client.client.info()

            # Connection metrics
            self._collect_connection_metrics(info)

            # Memory metrics
            self._collect_memory_metrics(info)

            # Performance metrics
            self._collect_performance_metrics(info)

            # Keyspace metrics
            await self._collect_keyspace_metrics(info)

            # Replication metrics
            self._collect_replication_metrics(info)

            # Slow query metrics
            await self._collect_slow_query_metrics()

        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            redis_errors.labels(error_type="metrics_collection").inc()

    def _collect_connection_metrics(self, info: dict):
        """Collect connection-related metrics."""
        redis_connections.set(info.get('connected_clients', 0))

        # Get pool stats if available
        if hasattr(self.redis_client, 'pool') and self.redis_client.pool:
            pool = self.redis_client.pool
            redis_connection_pool_size.set(pool.max_connections)
            # Pool usage would require custom tracking

    def _collect_memory_metrics(self, info: dict):
        """Collect memory-related metrics."""
        redis_memory_usage.set(info.get('used_memory', 0))
        redis_memory_peak.set(info.get('used_memory_peak', 0))
        redis_memory_fragmentation.set(
            float(info.get('mem_fragmentation_ratio', 1.0))
        )

    def _collect_performance_metrics(self, info: dict):
        """Collect performance-related metrics."""
        # Track expired and evicted keys
        expired = info.get('expired_keys', 0)
        evicted = info.get('evicted_keys', 0)

        # These are cumulative counters, so we track the increase
        redis_keys_expired._value._value = expired
        redis_keys_evicted._value._value = evicted

    async def _collect_keyspace_metrics(self, info: dict):
        """Collect keyspace-related metrics."""
        # Collect keys per database
        for key, value in info.items():
            if key.startswith('db'):
                db_num = key[2:]  # Extract database number
                if 'keys' in value:
                    redis_keys_total.labels(db=db_num).set(value['keys'])

    def _collect_replication_metrics(self, info: dict):
        """Collect replication-related metrics."""
        role = info.get('role', 'master')

        if role == 'master':
            redis_connected_slaves.set(info.get('connected_slaves', 0))

            # Calculate replication lag for each slave
            for i in range(info.get('connected_slaves', 0)):
                slave_info = info.get(f'slave{i}')
                if slave_info and 'lag' in slave_info:
                    lag = slave_info['lag']
                    if lag >= 0:  # -1 means unknown
                        redis_replication_lag.set(lag)

        elif role == 'slave':
            # For slaves, track master link status
            master_link_status = info.get('master_link_status', 'down')
            if master_link_status == 'down':
                redis_errors.labels(error_type="replication").inc()

    async def _collect_slow_query_metrics(self):
        """Collect slow query metrics."""
        try:
            slow_queries = await self.redis_client.get_slow_log(count=10)

            for query in slow_queries:
                if query['duration'] > self._slow_query_threshold:
                    redis_slow_queries.inc()
                    logger.warning(
                        f"Slow query detected: {query['command'][:100]} "
                        f"(duration: {query['duration']}μs)"
                    )

        except Exception as e:
            logger.error(f"Failed to collect slow query metrics: {e}")

    async def record_operation(self, operation: str, duration: float, success: bool):
        """Record a Redis operation for metrics.

        Args:
            operation: Operation name (get, set, delete, etc.)
            duration: Operation duration in seconds
            success: Whether the operation succeeded
        """
        if not PROMETHEUS_AVAILABLE:
            return

        status = "success" if success else "failure"
        redis_operations.labels(operation=operation, status=status).inc()
        redis_latency.labels(operation=operation).observe(duration)

    async def record_error(self, error_type: str):
        """Record a Redis error.

        Args:
            error_type: Type of error (connection, timeout, etc.)
        """
        if not PROMETHEUS_AVAILABLE:
            return

        redis_errors.labels(error_type=error_type).inc()

    async def record_reconnection(self):
        """Record a reconnection attempt."""
        if not PROMETHEUS_AVAILABLE:
            return

        redis_reconnections.inc()

    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current metrics."""
        try:
            info = await self.redis_client.client.info()

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "healthy" if self.redis_client._connected else "disconnected",
                "connection": {
                    "clients": info.get('connected_clients', 0),
                    "total_received": info.get('total_connections_received', 0)
                },
                "memory": {
                    "used": info.get('used_memory_human', 'N/A'),
                    "peak": info.get('used_memory_peak_human', 'N/A'),
                    "fragmentation": info.get('mem_fragmentation_ratio', 1.0)
                },
                "performance": {
                    "ops_per_sec": info.get('instantaneous_ops_per_sec', 0),
                    "total_commands": info.get('total_commands_processed', 0),
                    "keyspace_hits": info.get('keyspace_hits', 0),
                    "keyspace_misses": info.get('keyspace_misses', 0),
                    "hit_ratio": self._calculate_hit_ratio(info)
                },
                "persistence": {
                    "last_save": datetime.fromtimestamp(
                        info.get('rdb_last_save_time', 0)
                    ).isoformat() if info.get('rdb_last_save_time') else None,
                    "changes_since_save": info.get('rdb_changes_since_last_save', 0),
                    "aof_enabled": info.get('aof_enabled', 0) == 1
                },
                "replication": {
                    "role": info.get('role', 'unknown'),
                    "connected_slaves": info.get('connected_slaves', 0)
                }
            }
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "error": str(e)
            }

    def _calculate_hit_ratio(self, info: dict) -> float:
        """Calculate cache hit ratio."""
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        total = hits + misses

        if total == 0:
            return 0.0

        return round(hits / total * 100, 2)