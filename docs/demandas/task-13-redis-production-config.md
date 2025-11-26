# Prompt: Configurar Redis para Produção

Start Here
- Leia AGENTS.md e agents/README.md para padrões do repositório e checklists.
- Consulte docs/README.md para visão geral e guias (backend, frontend, database, auth).
- Siga os guias: agents/backend-development.md, agents/database-development.md, agents/security-check.md.

Objetivo
- Configurar Redis para ambiente de produção com alta disponibilidade e segurança.
- Implementar persistência, backups, monitoramento e otimizações de performance.
- Garantir resiliência e recuperação automática em caso de falhas.

Escopo
- Redis Cluster: configuração para alta disponibilidade.
- Persistência: AOF e RDB com políticas adequadas.
- Segurança: autenticação, TLS, ACL e firewall.
- Monitoramento: métricas, alertas e logs.
- Backup: estratégia de backup e restore.
- Performance: tuning e otimizações.

Requisitos de Configuração
- Variáveis de ambiente:
  - REDIS_URL=redis://username:password@host:6379/0
  - REDIS_MAX_CONNECTIONS=50
  - REDIS_CONNECTION_TIMEOUT=5
  - REDIS_SOCKET_TIMEOUT=5
  - REDIS_RETRY_ON_TIMEOUT=true
  - REDIS_SSL=true
  - REDIS_SSL_CERT_REQS=required
- Redis 7.0+ com módulos: RedisJSON, RediSearch (opcional)

Arquitetura de Alto Nível
- Redis Sentinel: 3 sentinels para failover automático
- Master-Replica: 1 master + 2 replicas
- Connection Pool: pooling com retry logic
- Circuit Breaker: proteção contra falhas em cascata
- Cache Layers: L1 (local) + L2 (Redis)

Configuração Redis (redis.conf)
```conf
# Network
bind 0.0.0.0
protected-mode yes
port 6379
tcp-backlog 511
timeout 300
tcp-keepalive 300

# General
daemonize yes
supervised systemd
pidfile /var/run/redis_6379.pid
loglevel notice
logfile /var/log/redis/redis-server.log
databases 16

# Security
requirepass ${REDIS_PASSWORD}
acl-pubsub-default allchannels

# ACL Configuration
aclfile /etc/redis/users.acl
# Example ACL:
# user websocket on +ping +info +get +set +del +exists +expire +ttl +zadd +zrem +zcard +zremrangebyscore ~ws:* ~rate_limit:* &* >websocket_password
# user app on +@all -flushall -flushdb -config -shutdown ~* &* >app_password

# Persistence
save 900 1      # After 900 sec if at least 1 key changed
save 300 10     # After 300 sec if at least 10 keys changed
save 60 10000   # After 60 sec if at least 10000 keys changed
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /var/lib/redis

# AOF
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
aof-load-truncated yes
aof-use-rdb-preamble yes

# Replication
replica-serve-stale-data yes
replica-read-only yes
repl-diskless-sync no
repl-diskless-sync-delay 5
repl-ping-replica-period 10
repl-timeout 60
repl-disable-tcp-nodelay no
repl-backlog-size 10mb
repl-backlog-ttl 3600

# Limits
maxclients 10000
maxmemory 2gb
maxmemory-policy allkeys-lru
maxmemory-samples 5

# Performance
lazyfree-lazy-eviction yes
lazyfree-lazy-expire yes
lazyfree-lazy-server-del yes
replica-lazy-flush yes
lazyfree-lazy-user-del yes

# Slow Log
slowlog-log-slower-than 10000
slowlog-max-len 128

# Client Output Buffer Limits
client-output-buffer-limit normal 0 0 0
client-output-buffer-limit replica 256mb 64mb 60
client-output-buffer-limit pubsub 32mb 8mb 60
```

Redis Sentinel Configuration
```conf
# sentinel.conf
port 26379
bind 0.0.0.0
protected-mode yes
dir /tmp
logfile /var/log/redis/sentinel.log
sentinel announce-ip ${PUBLIC_IP}
sentinel announce-port 26379

# Master monitoring
sentinel monitor mymaster ${MASTER_IP} 6379 2
sentinel auth-pass mymaster ${REDIS_PASSWORD}
sentinel down-after-milliseconds mymaster 5000
sentinel parallel-syncs mymaster 1
sentinel failover-timeout mymaster 180000

# Notification scripts
sentinel notification-script mymaster /etc/redis/notify.sh
sentinel client-reconfig-script mymaster /etc/redis/reconfig.sh
```

Docker Compose Production
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  redis-master:
    image: redis:7-alpine
    container_name: redis-master
    restart: always
    command: redis-server /usr/local/etc/redis/redis.conf
    volumes:
      - ./config/redis-master.conf:/usr/local/etc/redis/redis.conf
      - redis-master-data:/data
      - redis-master-logs:/var/log/redis
    ports:
      - "6379:6379"
    networks:
      - redis-net
    sysctls:
      - net.core.somaxconn=65535
    ulimits:
      nofile:
        soft: 65536
        hard: 65536

  redis-replica-1:
    image: redis:7-alpine
    container_name: redis-replica-1
    restart: always
    command: redis-server /usr/local/etc/redis/redis.conf --replicaof redis-master 6379
    volumes:
      - ./config/redis-replica.conf:/usr/local/etc/redis/redis.conf
      - redis-replica-1-data:/data
    depends_on:
      - redis-master
    networks:
      - redis-net

  redis-replica-2:
    image: redis:7-alpine
    container_name: redis-replica-2
    restart: always
    command: redis-server /usr/local/etc/redis/redis.conf --replicaof redis-master 6379
    volumes:
      - ./config/redis-replica.conf:/usr/local/etc/redis/redis.conf
      - redis-replica-2-data:/data
    depends_on:
      - redis-master
    networks:
      - redis-net

  redis-sentinel-1:
    image: redis:7-alpine
    container_name: redis-sentinel-1
    restart: always
    command: redis-sentinel /usr/local/etc/redis/sentinel.conf
    volumes:
      - ./config/sentinel.conf:/usr/local/etc/redis/sentinel.conf
    depends_on:
      - redis-master
      - redis-replica-1
      - redis-replica-2
    networks:
      - redis-net

  redis-sentinel-2:
    image: redis:7-alpine
    container_name: redis-sentinel-2
    restart: always
    command: redis-sentinel /usr/local/etc/redis/sentinel.conf
    volumes:
      - ./config/sentinel.conf:/usr/local/etc/redis/sentinel.conf
    depends_on:
      - redis-master
    networks:
      - redis-net

  redis-sentinel-3:
    image: redis:7-alpine
    container_name: redis-sentinel-3
    restart: always
    command: redis-sentinel /usr/local/etc/redis/sentinel.conf
    volumes:
      - ./config/sentinel.conf:/usr/local/etc/redis/sentinel.conf
    depends_on:
      - redis-master
    networks:
      - redis-net

volumes:
  redis-master-data:
  redis-replica-1-data:
  redis-replica-2-data:
  redis-master-logs:

networks:
  redis-net:
    driver: bridge
```

Python Redis Client com Resiliência
```python
# backend/src/infrastructure/cache/redis_client.py
import redis.asyncio as redis
from redis.sentinel import Sentinel
from redis.asyncio import ConnectionPool
from redis.backoff import ExponentialBackoff
from redis.retry import Retry
from typing import Optional, Any
import ssl
from loguru import logger

class ResilientRedisClient:
    def __init__(self, config: dict):
        self.config = config
        self.client: Optional[redis.Redis] = None
        self.sentinel: Optional[Sentinel] = None
        self.pool: Optional[ConnectionPool] = None

    async def connect(self):
        """Connect to Redis with Sentinel support."""
        try:
            if self.config.get("use_sentinel"):
                # Sentinel configuration
                sentinels = [
                    (host, port)
                    for host, port in self.config["sentinels"]
                ]

                self.sentinel = Sentinel(
                    sentinels,
                    socket_connect_timeout=self.config["timeout"],
                    password=self.config["password"],
                    sentinel_kwargs={"password": self.config["sentinel_password"]}
                )

                # Get master from sentinel
                self.client = self.sentinel.master_for(
                    self.config["master_name"],
                    socket_timeout=self.config["timeout"],
                    connection_pool_class=redis.BlockingConnectionPool,
                    max_connections=self.config["max_connections"],
                    retry_on_timeout=True,
                    retry=Retry(
                        ExponentialBackoff(),
                        retries=3
                    )
                )
            else:
                # Direct connection with connection pool
                ssl_config = None
                if self.config.get("ssl"):
                    ssl_config = ssl.create_default_context()
                    if self.config.get("ssl_cert_path"):
                        ssl_config.load_verify_locations(
                            self.config["ssl_cert_path"]
                        )

                self.pool = ConnectionPool(
                    host=self.config["host"],
                    port=self.config["port"],
                    password=self.config["password"],
                    db=self.config.get("db", 0),
                    max_connections=self.config["max_connections"],
                    socket_connect_timeout=self.config["timeout"],
                    socket_timeout=self.config["timeout"],
                    retry_on_timeout=True,
                    health_check_interval=30,
                    ssl=ssl_config is not None,
                    ssl_context=ssl_config
                )

                self.client = redis.Redis(
                    connection_pool=self.pool,
                    decode_responses=True
                )

            # Test connection
            await self.client.ping()
            logger.info("Redis connection established")

        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise

    async def get_with_fallback(
        self,
        key: str,
        fallback_fn=None
    ) -> Optional[Any]:
        """Get value with fallback on failure."""
        try:
            value = await self.client.get(key)
            if value is None and fallback_fn:
                value = await fallback_fn()
                if value is not None:
                    await self.set_with_retry(key, value)
            return value
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            if fallback_fn:
                return await fallback_fn()
            return None

    async def set_with_retry(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
        retries: int = 3
    ) -> bool:
        """Set value with retry logic."""
        for attempt in range(retries):
            try:
                return await self.client.set(key, value, ex=ex)
            except Exception as e:
                if attempt == retries - 1:
                    logger.error(f"Redis set failed after {retries} attempts: {e}")
                    return False
                await asyncio.sleep(2 ** attempt)
        return False

    async def health_check(self) -> dict:
        """Check Redis health status."""
        try:
            # Ping
            await self.client.ping()

            # Get info
            info = await self.client.info()

            # Get memory usage
            memory = await self.client.memory_stats()

            return {
                "status": "healthy",
                "connected_clients": info.get("connected_clients"),
                "used_memory": info.get("used_memory_human"),
                "uptime_seconds": info.get("uptime_in_seconds"),
                "role": info.get("role"),
                "connected_slaves": info.get("connected_slaves", 0)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def disconnect(self):
        """Gracefully disconnect."""
        if self.client:
            await self.client.close()
        if self.pool:
            await self.pool.disconnect()
```

Monitoramento e Alertas
```python
# backend/src/infrastructure/monitoring/redis_monitor.py
import asyncio
from prometheus_client import Gauge, Counter, Histogram

# Metrics
redis_connections = Gauge('redis_connections', 'Number of Redis connections')
redis_memory_usage = Gauge('redis_memory_usage_bytes', 'Redis memory usage')
redis_operations = Counter('redis_operations_total', 'Total Redis operations', ['operation'])
redis_latency = Histogram('redis_operation_duration_seconds', 'Redis operation latency', ['operation'])

class RedisMonitor:
    def __init__(self, redis_client):
        self.redis_client = redis_client

    async def collect_metrics(self):
        """Collect Redis metrics."""
        while True:
            try:
                info = await self.redis_client.info()

                # Update metrics
                redis_connections.set(info['connected_clients'])
                redis_memory_usage.set(info['used_memory'])

                # Check slow queries
                slow_log = await self.redis_client.slowlog_get(10)
                for entry in slow_log:
                    if entry['duration'] > 10000:  # >10ms
                        logger.warning(f"Slow query detected: {entry}")

                await asyncio.sleep(60)  # Collect every minute

            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(60)
```

Backup Strategy
```bash
#!/bin/bash
# backup-redis.sh

BACKUP_DIR="/var/backups/redis"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="redis_backup_${TIMESTAMP}.rdb"

# Create backup directory
mkdir -p $BACKUP_DIR

# Trigger BGSAVE
redis-cli -a $REDIS_PASSWORD BGSAVE

# Wait for backup to complete
while [ $(redis-cli -a $REDIS_PASSWORD LASTSAVE) -eq $(redis-cli -a $REDIS_PASSWORD LASTSAVE) ]; do
    sleep 1
done

# Copy backup file
cp /var/lib/redis/dump.rdb $BACKUP_DIR/$BACKUP_FILE

# Compress backup
gzip $BACKUP_DIR/$BACKUP_FILE

# Upload to S3 (optional)
aws s3 cp $BACKUP_DIR/${BACKUP_FILE}.gz s3://backups/redis/

# Cleanup old backups (keep 7 days)
find $BACKUP_DIR -name "redis_backup_*.gz" -mtime +7 -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
```

Performance Tuning
- Kernel parameters (sysctl.conf):
  ```
  vm.overcommit_memory = 1
  net.core.somaxconn = 65535
  net.ipv4.tcp_max_syn_backlog = 65535
  ```
- Disable Transparent Huge Pages (THP)
- Use dedicated network for Redis traffic
- Monitor slow queries and optimize
- Use pipelining for bulk operations
- Implement circuit breaker pattern

Segurança
- Usar ACL para diferentes usuários/aplicações
- TLS/SSL para comunicação encriptada
- Firewall rules limitando acesso
- Audit logging de comandos sensíveis
- Regular security patches
- Desabilitar comandos perigosos (FLUSHDB, CONFIG)

Testes de Resiliência
```python
# backend/tests/test_redis_resilience.py
import pytest
import asyncio

async def test_failover_recovery():
    """Test automatic failover and recovery."""
    client = ResilientRedisClient(config)
    await client.connect()

    # Set value
    await client.set_with_retry("test_key", "test_value")

    # Simulate master failure
    # (In real test, would stop master container)

    # Wait for failover
    await asyncio.sleep(10)

    # Should still work with new master
    value = await client.get_with_fallback("test_key")
    assert value == "test_value"

async def test_connection_pool_exhaustion():
    """Test behavior under connection pool exhaustion."""
    # Create many concurrent connections
    tasks = []
    for i in range(100):
        tasks.append(client.get_with_fallback(f"key_{i}"))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Should handle gracefully
    successful = sum(1 for r in results if not isinstance(r, Exception))
    assert successful > 0
```

Entregáveis do PR
- Redis production configuration files
- Docker Compose para ambiente HA
- Resilient Redis client implementation
- Monitoring and metrics collection
- Backup and restore scripts
- Performance tuning documentation
- Security hardening checklist
- Disaster recovery procedures

Checklists úteis
- Revisar agents/database-development.md para patterns
- Seguir agents/security-check.md para hardening
- Validar com agents/backend-development.md

Notas
- Considerar Redis Cluster para >100GB de dados
- Usar Redis Streams para event sourcing
- Implementar cache warming strategies
- Monitorar memory fragmentation
- Considerar usar KeyDB como alternativa compatível