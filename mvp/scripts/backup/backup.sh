#!/bin/bash

# ContentGrün Automated Backup Script with Rotation
# Runs daily at 3 AM via cron
# Keeps: Last 7 daily backups + Last 4 weekly backups (Sundays)
# Stores backups in /opt/contentgruen-backups/ on HOST filesystem

set -e  # Exit on error

# Configuration
BACKUP_ROOT="/opt/contentgruen-backups"
DAILY_DIR="$BACKUP_ROOT/daily"
WEEKLY_DIR="$BACKUP_ROOT/weekly"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DAY_OF_WEEK=$(date +%u)  # 1=Monday, 7=Sunday
BACKUP_DIR="$DAILY_DIR/backup_$TIMESTAMP"
POSTGRES_CONTAINER="contentgruen-app-postgres"
APP_CONTAINER="contentgruen-semantic-search"
QDRANT_CONTAINER="contentgruen-qdrant"
DB_NAME="contentgruen_app"
DB_USER="app_user"

# Retention settings
KEEP_DAILY=7
KEEP_WEEKLY=4

# Log file
LOG_FILE="$BACKUP_ROOT/backup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to log with timestamp
log() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG_FILE"
}

log "${GREEN}========================================${NC}"
log "${GREEN}ContentGrün Automated Backup${NC}"
log "${GREEN}========================================${NC}"
log "Backup timestamp: $TIMESTAMP"
log "Day of week: $DAY_OF_WEEK (1=Mon, 7=Sun)"

# Create backup directories
mkdir -p "$DAILY_DIR"
mkdir -p "$WEEKLY_DIR"
mkdir -p "$BACKUP_DIR"

# Check if containers are running
log "\n${YELLOW}Checking Docker containers...${NC}"
if ! docker ps | grep -q "$POSTGRES_CONTAINER"; then
    log "${RED}Error: PostgreSQL container '$POSTGRES_CONTAINER' is not running${NC}"
    exit 1
fi

if ! docker ps | grep -q "$APP_CONTAINER"; then
    log "${RED}Error: Application container '$APP_CONTAINER' is not running${NC}"
    exit 1
fi

if ! docker ps | grep -q "$QDRANT_CONTAINER"; then
    log "${RED}Error: Qdrant container '$QDRANT_CONTAINER' is not running${NC}"
    exit 1
fi

log "All containers are running"

# Backup Qdrant collection
log "\n${YELLOW}Backing up Qdrant collection...${NC}"
docker exec "$APP_CONTAINER" python /app/scripts/backup_qdrant.py \
    --output /backups/daily/backup_$TIMESTAMP/qdrant_snapshot.tar

if [ $? -eq 0 ]; then
    log "${GREEN}✓ Qdrant backup completed${NC}"
    if [ -f "$BACKUP_DIR/qdrant_snapshot.tar" ]; then
        QDRANT_SIZE=$(du -h "$BACKUP_DIR/qdrant_snapshot.tar" | cut -f1)
        log "  Size: $QDRANT_SIZE"
    fi
else
    log "${RED}✗ Qdrant backup failed${NC}"
    exit 1
fi

# Backup PostgreSQL database
log "\n${YELLOW}Backing up PostgreSQL database...${NC}"
docker exec "$POSTGRES_CONTAINER" pg_dump \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-privileges \
    --if-exists \
    --clean \
    --create \
    > "$BACKUP_DIR/postgresql.sql"

if [ $? -eq 0 ]; then
    log "${GREEN}✓ PostgreSQL backup completed${NC}"
    PG_SIZE=$(du -h "$BACKUP_DIR/postgresql.sql" | cut -f1)
    log "  Size: $PG_SIZE"
else
    log "${RED}✗ PostgreSQL backup failed${NC}"
    exit 1
fi

# Create metadata file
log "\n${YELLOW}Creating metadata file...${NC}"
cat > "$BACKUP_DIR/metadata.json" << EOF
{
    "version": "1.0",
    "timestamp": "$TIMESTAMP",
    "created_at": "$(date -Iseconds)",
    "host": "$(hostname)",
    "backup_type": "daily",
    "day_of_week": $DAY_OF_WEEK,
    "containers": {
        "postgres": "$POSTGRES_CONTAINER",
        "application": "$APP_CONTAINER",
        "qdrant": "$QDRANT_CONTAINER"
    },
    "files": {
        "qdrant_snapshot": {
            "filename": "qdrant_snapshot.tar",
            "size": $(stat -c%s "$BACKUP_DIR/qdrant_snapshot.tar" 2>/dev/null || echo 0),
            "checksum": "$(md5sum "$BACKUP_DIR/qdrant_snapshot.tar" | cut -d' ' -f1)"
        },
        "postgresql": {
            "filename": "postgresql.sql",
            "size": $(stat -c%s "$BACKUP_DIR/postgresql.sql" 2>/dev/null || echo 0),
            "checksum": "$(md5sum "$BACKUP_DIR/postgresql.sql" | cut -d' ' -f1)"
        }
    }
}
EOF

log "${GREEN}✓ Metadata file created${NC}"

# Weekly backup (copy to weekly directory on Sunday)
if [ "$DAY_OF_WEEK" -eq 7 ]; then
    log "\n${YELLOW}Creating weekly backup (Sunday)...${NC}"
    WEEKLY_BACKUP_DIR="$WEEKLY_DIR/backup_$TIMESTAMP"
    cp -r "$BACKUP_DIR" "$WEEKLY_BACKUP_DIR"

    # Update metadata to mark as weekly
    sed -i 's/"backup_type": "daily"/"backup_type": "weekly"/' "$WEEKLY_BACKUP_DIR/metadata.json"

    log "${GREEN}✓ Weekly backup created${NC}"

    # Update weekly latest symlink
    rm -f "$WEEKLY_DIR/latest"
    ln -s "$WEEKLY_BACKUP_DIR" "$WEEKLY_DIR/latest"
fi

# Update daily latest symlink
rm -f "$DAILY_DIR/latest"
ln -s "$BACKUP_DIR" "$DAILY_DIR/latest"

# Rotation: Remove old daily backups (keep last 7)
log "\n${YELLOW}Rotating daily backups (keeping last $KEEP_DAILY)...${NC}"
cd "$DAILY_DIR"
DAILY_COUNT=$(ls -dt backup_* 2>/dev/null | wc -l)
if [ "$DAILY_COUNT" -gt "$KEEP_DAILY" ]; then
    REMOVED=$(ls -dt backup_* 2>/dev/null | tail -n +$((KEEP_DAILY + 1)) | wc -l)
    ls -dt backup_* 2>/dev/null | tail -n +$((KEEP_DAILY + 1)) | xargs rm -rf 2>/dev/null || true
    log "${GREEN}✓ Removed $REMOVED old daily backup(s)${NC}"
else
    log "No daily backups to remove (have $DAILY_COUNT, keeping $KEEP_DAILY)"
fi

# Rotation: Remove old weekly backups (keep last 4)
log "\n${YELLOW}Rotating weekly backups (keeping last $KEEP_WEEKLY)...${NC}"
cd "$WEEKLY_DIR"
WEEKLY_COUNT=$(ls -dt backup_* 2>/dev/null | wc -l)
if [ "$WEEKLY_COUNT" -gt "$KEEP_WEEKLY" ]; then
    REMOVED=$(ls -dt backup_* 2>/dev/null | tail -n +$((KEEP_WEEKLY + 1)) | wc -l)
    ls -dt backup_* 2>/dev/null | tail -n +$((KEEP_WEEKLY + 1)) | xargs rm -rf 2>/dev/null || true
    log "${GREEN}✓ Removed $REMOVED old weekly backup(s)${NC}"
else
    log "No weekly backups to remove (have $WEEKLY_COUNT, keeping $KEEP_WEEKLY)"
fi

# Disk usage summary
log "\n${YELLOW}Disk usage summary:${NC}"
TOTAL_SIZE=$(du -sh "$BACKUP_ROOT" 2>/dev/null | cut -f1)
DAILY_SIZE=$(du -sh "$DAILY_DIR" 2>/dev/null | cut -f1)
WEEKLY_SIZE=$(du -sh "$WEEKLY_DIR" 2>/dev/null | cut -f1)
log "Total backup storage: $TOTAL_SIZE"
log "  Daily backups: $DAILY_SIZE (count: $DAILY_COUNT)"
log "  Weekly backups: $WEEKLY_SIZE (count: $WEEKLY_COUNT)"

# Summary
log "\n${GREEN}========================================${NC}"
log "${GREEN}Backup completed successfully!${NC}"
log "${GREEN}========================================${NC}"
log "Location: $BACKUP_DIR"
log "Type: Daily backup"
[ "$DAY_OF_WEEK" -eq 7 ] && log "Also saved as weekly backup"
log ""
log "To restore this backup, run:"
log "  cd /opt/contentgruen/mvp/scripts/backup"
log "  ./restore.sh $DAILY_DIR/backup_$TIMESTAMP"
