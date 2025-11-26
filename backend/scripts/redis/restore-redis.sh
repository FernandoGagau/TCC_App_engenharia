#!/bin/bash
# Redis Restore Script
# Restores Redis data from backup file

set -e

# Configuration
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/redis}"
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

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -f, --file <backup_file>    Specific backup file to restore"
    echo "  -l, --latest                Restore from latest backup (default)"
    echo "  -s, --from-s3               Download backup from S3"
    echo "  -d, --date <YYYYMMDD>      Restore backup from specific date"
    echo "  -y, --yes                   Skip confirmation prompt"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --latest                 # Restore latest local backup"
    echo "  $0 --from-s3 --latest       # Restore latest S3 backup"
    echo "  $0 --file backup.tar.gz     # Restore specific file"
    echo "  $0 --date 20240101          # Restore backup from date"
    exit 0
}

# Parse arguments
BACKUP_FILE=""
USE_LATEST=true
FROM_S3=false
SPECIFIC_DATE=""
SKIP_CONFIRM=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--file)
            BACKUP_FILE="$2"
            USE_LATEST=false
            shift 2
            ;;
        -l|--latest)
            USE_LATEST=true
            shift
            ;;
        -s|--from-s3)
            FROM_S3=true
            shift
            ;;
        -d|--date)
            SPECIFIC_DATE="$2"
            USE_LATEST=false
            shift 2
            ;;
        -y|--yes)
            SKIP_CONFIRM=true
            shift
            ;;
        -h|--help)
            show_usage
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            ;;
    esac
done

# Check requirements
command -v redis-cli >/dev/null 2>&1 || { log_error "redis-cli is required but not installed."; exit 1; }

# Build redis-cli command
REDIS_CLI="redis-cli -h $REDIS_HOST -p $REDIS_PORT"
if [ -n "$REDIS_PASSWORD" ]; then
    REDIS_CLI="$REDIS_CLI -a $REDIS_PASSWORD"
fi

# Check Redis connection
if ! $REDIS_CLI ping > /dev/null 2>&1; then
    log_error "Cannot connect to Redis at $REDIS_HOST:$REDIS_PORT"
    exit 1
fi

# Download from S3 if requested
if [ "$FROM_S3" = true ]; then
    if [ -z "$S3_BUCKET" ]; then
        log_error "S3_BUCKET environment variable not set"
        exit 1
    fi

    if ! command -v aws >/dev/null 2>&1; then
        log_error "AWS CLI is required for S3 operations but not installed"
        exit 1
    fi

    log_info "Listing available S3 backups..."

    if [ "$USE_LATEST" = true ]; then
        # Get latest backup from S3
        BACKUP_FILE=$(aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}/" | \
            grep "redis_backup_.*\.tar\.gz$" | \
            sort | tail -1 | awk '{print $4}')

        if [ -z "$BACKUP_FILE" ]; then
            log_error "No backups found in S3"
            exit 1
        fi
    elif [ -n "$SPECIFIC_DATE" ]; then
        # Get backup from specific date
        BACKUP_FILE=$(aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}/" | \
            grep "redis_backup_${SPECIFIC_DATE}" | \
            grep "\.tar\.gz$" | \
            head -1 | awk '{print $4}')

        if [ -z "$BACKUP_FILE" ]; then
            log_error "No backup found for date: $SPECIFIC_DATE"
            exit 1
        fi
    fi

    # Download backup
    log_info "Downloading backup: $BACKUP_FILE"
    mkdir -p "$BACKUP_DIR"

    if ! aws s3 cp "s3://${S3_BUCKET}/${S3_PREFIX}/${BACKUP_FILE}" "$BACKUP_DIR/${BACKUP_FILE}"; then
        log_error "Failed to download backup from S3"
        exit 1
    fi

    # Download checksum if available
    if aws s3 cp "s3://${S3_BUCKET}/${S3_PREFIX}/${BACKUP_FILE}.sha256" "$BACKUP_DIR/${BACKUP_FILE}.sha256" 2>/dev/null; then
        log_info "Verifying backup integrity..."
        cd "$BACKUP_DIR"
        if ! sha256sum -c "${BACKUP_FILE}.sha256"; then
            log_error "Backup file integrity check failed"
            exit 1
        fi
        log_info "Backup integrity verified"
    fi

    BACKUP_FILE="$BACKUP_DIR/$BACKUP_FILE"
else
    # Use local backup
    if [ "$USE_LATEST" = true ]; then
        # Find latest backup
        BACKUP_FILE=$(ls -t "$BACKUP_DIR"/redis_backup_*.tar.gz 2>/dev/null | head -1)

        if [ -z "$BACKUP_FILE" ]; then
            log_error "No backup files found in $BACKUP_DIR"
            exit 1
        fi
    elif [ -n "$SPECIFIC_DATE" ]; then
        # Find backup from specific date
        BACKUP_FILE=$(ls -t "$BACKUP_DIR"/redis_backup_${SPECIFIC_DATE}*.tar.gz 2>/dev/null | head -1)

        if [ -z "$BACKUP_FILE" ]; then
            log_error "No backup found for date: $SPECIFIC_DATE"
            exit 1
        fi
    elif [ -n "$BACKUP_FILE" ]; then
        # Check if specified file exists
        if [ ! -f "$BACKUP_FILE" ]; then
            # Try in backup directory
            if [ -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
                BACKUP_FILE="$BACKUP_DIR/$BACKUP_FILE"
            else
                log_error "Backup file not found: $BACKUP_FILE"
                exit 1
            fi
        fi
    fi
fi

log_info "Selected backup: $BACKUP_FILE"

# Extract backup metadata
TEMP_DIR=$(mktemp -d)
log_info "Extracting backup to $TEMP_DIR..."

if ! tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"; then
    log_error "Failed to extract backup file"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Find RDB file
RDB_FILE=$(find "$TEMP_DIR" -name "*.rdb" | head -1)
if [ -z "$RDB_FILE" ]; then
    log_error "No RDB file found in backup"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Display backup metadata if available
META_FILE=$(find "$TEMP_DIR" -name "*.meta" | head -1)
if [ -f "$META_FILE" ]; then
    log_info "Backup metadata:"
    cat "$META_FILE" | python3 -m json.tool 2>/dev/null || cat "$META_FILE"
fi

# Get current Redis state
log_info "Current Redis state:"
CURRENT_KEYS=$($REDIS_CLI DBSIZE | cut -d' ' -f1)
CURRENT_MEMORY=$($REDIS_CLI INFO memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')
log_info "  Keys: $CURRENT_KEYS"
log_info "  Memory: $CURRENT_MEMORY"

# Confirmation prompt
if [ "$SKIP_CONFIRM" = false ]; then
    echo ""
    log_warn "WARNING: This will replace ALL current Redis data!"
    read -p "Are you sure you want to continue? (yes/no): " CONFIRM

    if [ "$CONFIRM" != "yes" ]; then
        log_info "Restore cancelled"
        rm -rf "$TEMP_DIR"
        exit 0
    fi
fi

# Create backup of current data
log_info "Creating backup of current data..."
SAFETY_BACKUP="redis_pre_restore_$(date +%Y%m%d_%H%M%S)"
$REDIS_CLI BGSAVE > /dev/null

# Wait for safety backup to complete
LASTSAVE_BEFORE=$($REDIS_CLI LASTSAVE | tr -d '\r')
while true; do
    LASTSAVE_AFTER=$($REDIS_CLI LASTSAVE | tr -d '\r')
    if [ "$LASTSAVE_AFTER" -gt "$LASTSAVE_BEFORE" ]; then
        break
    fi
    sleep 1
done

# Get Redis config
REDIS_DIR=$($REDIS_CLI CONFIG GET dir | tail -1 | tr -d '\r')
REDIS_DBFILENAME=$($REDIS_CLI CONFIG GET dbfilename | tail -1 | tr -d '\r')

# Copy current dump as safety backup
if [ -f "$REDIS_DIR/$REDIS_DBFILENAME" ]; then
    cp "$REDIS_DIR/$REDIS_DBFILENAME" "$BACKUP_DIR/${SAFETY_BACKUP}.rdb"
    log_info "Safety backup created: ${SAFETY_BACKUP}.rdb"
fi

# Stop Redis from saving during restore
log_info "Disabling auto-save during restore..."
$REDIS_CLI CONFIG SET save "" > /dev/null

# Clear current data
log_info "Clearing current Redis data..."
$REDIS_CLI FLUSHALL > /dev/null

# Copy new RDB file
log_info "Copying restore file..."
cp "$RDB_FILE" "$REDIS_DIR/$REDIS_DBFILENAME"

# Restart Redis to load new data
log_info "Restarting Redis to load new data..."
if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl restart redis
elif command -v service >/dev/null 2>&1; then
    sudo service redis-server restart
else
    log_warn "Cannot restart Redis automatically. Please restart Redis manually."
    log_info "You can load the data by running: redis-cli SHUTDOWN NOSAVE && redis-server"
fi

# Wait for Redis to come back up
log_info "Waiting for Redis to restart..."
sleep 5

MAX_WAIT=30
WAITED=0
while ! $REDIS_CLI ping > /dev/null 2>&1; do
    sleep 1
    WAITED=$((WAITED + 1))
    if [ $WAITED -ge $MAX_WAIT ]; then
        log_error "Redis did not come back up after $MAX_WAIT seconds"
        exit 1
    fi
done

# Re-enable auto-save
log_info "Re-enabling auto-save..."
$REDIS_CLI CONFIG SET save "900 1 300 10 60 10000" > /dev/null

# Verify restoration
log_info "Verifying restoration..."
RESTORED_KEYS=$($REDIS_CLI DBSIZE | cut -d' ' -f1)
RESTORED_MEMORY=$($REDIS_CLI INFO memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')

log_info "Restoration complete!"
log_info "  Keys restored: $RESTORED_KEYS"
log_info "  Memory used: $RESTORED_MEMORY"

# Restore AOF if it was included
AOF_FILE=$(find "$TEMP_DIR" -name "*.aof" | head -1)
if [ -f "$AOF_FILE" ]; then
    AOF_ENABLED=$($REDIS_CLI CONFIG GET appendonly | tail -1 | tr -d '\r')
    if [ "$AOF_ENABLED" = "yes" ]; then
        log_info "Restoring AOF file..."
        AOF_FILENAME=$($REDIS_CLI CONFIG GET appendfilename | tail -1 | tr -d '\r')
        cp "$AOF_FILE" "$REDIS_DIR/$AOF_FILENAME"
        log_info "AOF file restored"
    fi
fi

# Cleanup
rm -rf "$TEMP_DIR"

# Send notification if webhook is configured
if [ -n "$SLACK_WEBHOOK_URL" ]; then
    curl -X POST "$SLACK_WEBHOOK_URL" \
        -H 'Content-Type: application/json' \
        -d "{\"text\":\"✅ Redis restore completed: $RESTORED_KEYS keys restored\"}" \
        2>/dev/null || log_warn "Failed to send Slack notification"
fi

log_info "Redis restore completed successfully!"

exit 0