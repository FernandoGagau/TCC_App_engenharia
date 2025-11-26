#!/bin/bash
# Redis Backup Script
# Performs automated backup of Redis data with compression and optional S3 upload

set -e

# Configuration
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/redis}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="redis_backup_${TIMESTAMP}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
S3_BUCKET="${S3_BUCKET}"
S3_PREFIX="${S3_PREFIX:-redis-backups}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check requirements
command -v redis-cli >/dev/null 2>&1 || { log_error "redis-cli is required but not installed."; exit 1; }

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Build redis-cli command
REDIS_CLI="redis-cli -h $REDIS_HOST -p $REDIS_PORT"
if [ -n "$REDIS_PASSWORD" ]; then
    REDIS_CLI="$REDIS_CLI -a $REDIS_PASSWORD"
fi

log_info "Starting Redis backup..."
log_info "Host: $REDIS_HOST:$REDIS_PORT"
log_info "Backup directory: $BACKUP_DIR"

# Check Redis connection
if ! $REDIS_CLI ping > /dev/null 2>&1; then
    log_error "Cannot connect to Redis"
    exit 1
fi

# Get Redis info
REDIS_ROLE=$($REDIS_CLI INFO replication | grep "role:" | cut -d: -f2 | tr -d '\r')
log_info "Redis role: $REDIS_ROLE"

# Trigger BGSAVE
log_info "Triggering background save..."
LASTSAVE_BEFORE=$($REDIS_CLI LASTSAVE | tr -d '\r')
$REDIS_CLI BGSAVE > /dev/null

# Wait for backup to complete
log_info "Waiting for backup to complete..."
while true; do
    LASTSAVE_AFTER=$($REDIS_CLI LASTSAVE | tr -d '\r')
    if [ "$LASTSAVE_AFTER" -gt "$LASTSAVE_BEFORE" ]; then
        break
    fi
    sleep 1
done

log_info "Background save completed"

# Get Redis data directory
REDIS_DIR=$($REDIS_CLI CONFIG GET dir | tail -1 | tr -d '\r')
REDIS_DBFILENAME=$($REDIS_CLI CONFIG GET dbfilename | tail -1 | tr -d '\r')

# Copy backup file
if [ -f "$REDIS_DIR/$REDIS_DBFILENAME" ]; then
    cp "$REDIS_DIR/$REDIS_DBFILENAME" "$BACKUP_DIR/${BACKUP_FILE}.rdb"
    log_info "Backup file copied to $BACKUP_DIR/${BACKUP_FILE}.rdb"
else
    log_error "Redis dump file not found at $REDIS_DIR/$REDIS_DBFILENAME"
    exit 1
fi

# Also backup AOF if enabled
AOF_ENABLED=$($REDIS_CLI CONFIG GET appendonly | tail -1 | tr -d '\r')
if [ "$AOF_ENABLED" = "yes" ]; then
    AOF_FILENAME=$($REDIS_CLI CONFIG GET appendfilename | tail -1 | tr -d '\r')
    if [ -f "$REDIS_DIR/$AOF_FILENAME" ]; then
        cp "$REDIS_DIR/$AOF_FILENAME" "$BACKUP_DIR/${BACKUP_FILE}.aof"
        log_info "AOF file copied to $BACKUP_DIR/${BACKUP_FILE}.aof"
    fi
fi

# Create metadata file
cat > "$BACKUP_DIR/${BACKUP_FILE}.meta" <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "redis_version": "$($REDIS_CLI INFO server | grep redis_version | cut -d: -f2 | tr -d '\r')",
  "redis_mode": "$($REDIS_CLI INFO server | grep redis_mode | cut -d: -f2 | tr -d '\r')",
  "role": "$REDIS_ROLE",
  "used_memory": "$($REDIS_CLI INFO memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')",
  "db_count": "$($REDIS_CLI INFO keyspace | grep -c '^db' || echo 0)",
  "total_keys": "$($REDIS_CLI DBSIZE | cut -d' ' -f1)",
  "host": "$REDIS_HOST",
  "port": "$REDIS_PORT"
}
EOF

# Compress backup
log_info "Compressing backup..."
cd "$BACKUP_DIR"
tar -czf "${BACKUP_FILE}.tar.gz" \
    "${BACKUP_FILE}.rdb" \
    "${BACKUP_FILE}.meta" \
    $([ -f "${BACKUP_FILE}.aof" ] && echo "${BACKUP_FILE}.aof")

# Calculate checksums
sha256sum "${BACKUP_FILE}.tar.gz" > "${BACKUP_FILE}.tar.gz.sha256"

# Remove uncompressed files
rm -f "${BACKUP_FILE}.rdb" "${BACKUP_FILE}.aof" "${BACKUP_FILE}.meta"

BACKUP_SIZE=$(du -h "${BACKUP_FILE}.tar.gz" | cut -f1)
log_info "Backup compressed: ${BACKUP_FILE}.tar.gz (${BACKUP_SIZE})"

# Upload to S3 if configured
if [ -n "$S3_BUCKET" ]; then
    if command -v aws >/dev/null 2>&1; then
        log_info "Uploading to S3..."

        # Upload backup
        if aws s3 cp "${BACKUP_FILE}.tar.gz" "s3://${S3_BUCKET}/${S3_PREFIX}/${BACKUP_FILE}.tar.gz"; then
            log_info "Backup uploaded to S3"

            # Upload checksum
            aws s3 cp "${BACKUP_FILE}.tar.gz.sha256" "s3://${S3_BUCKET}/${S3_PREFIX}/${BACKUP_FILE}.tar.gz.sha256"

            # Set lifecycle if this is a daily backup
            if [ "$(date +%H)" = "00" ]; then
                aws s3api put-object-tagging \
                    --bucket "$S3_BUCKET" \
                    --key "${S3_PREFIX}/${BACKUP_FILE}.tar.gz" \
                    --tagging '{"TagSet":[{"Key":"Type","Value":"daily"}]}'
            fi
        else
            log_warn "Failed to upload to S3"
        fi
    else
        log_warn "AWS CLI not installed, skipping S3 upload"
    fi
fi

# Cleanup old backups
log_info "Cleaning up old backups (keeping last $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "redis_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "redis_backup_*.tar.gz.sha256" -mtime +$RETENTION_DAYS -delete

# List recent backups
log_info "Recent backups:"
ls -lht "$BACKUP_DIR"/redis_backup_*.tar.gz 2>/dev/null | head -5

log_info "Backup completed successfully: ${BACKUP_FILE}.tar.gz"

# Send notification if webhook is configured
if [ -n "$SLACK_WEBHOOK_URL" ]; then
    curl -X POST "$SLACK_WEBHOOK_URL" \
        -H 'Content-Type: application/json' \
        -d "{\"text\":\"✅ Redis backup completed: ${BACKUP_FILE}.tar.gz (${BACKUP_SIZE})\"}" \
        2>/dev/null || log_warn "Failed to send Slack notification"
fi

exit 0