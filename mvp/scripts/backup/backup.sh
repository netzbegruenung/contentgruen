#!/bin/bash

# Gut gesagt Automated Backup Script with Rotation
# Runs daily at 3 AM via cron
# Keeps: Last 7 daily backups + Last 4 weekly backups (Sundays)
# Stores backups in /opt/gutgesagt-backups/ on HOST filesystem

set -e  # Exit on error

# Configuration
# Host-Seite des Mounts /backups im Application-Container; beide muessen zusammenpassen.
BACKUP_ROOT="${BACKUP_ROOT:-/opt/gutgesagt-backups}"
DAILY_DIR="$BACKUP_ROOT/daily"
WEEKLY_DIR="$BACKUP_ROOT/weekly"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DAY_OF_WEEK=$(date +%u)  # 1=Monday, 7=Sunday
BACKUP_DIR="$DAILY_DIR/backup_$TIMESTAMP"
# Containernamen: Dev, Test und Prod nutzen dieselben Namen. Abweichende Namen
# kommen aus der Umgebung, z. B.:
#   POSTGRES_CONTAINER=anderer-name ./backup.sh
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-gutgesagt-app-postgres}"
APP_CONTAINER="${APP_CONTAINER:-gutgesagt-semantic-search}"
QDRANT_CONTAINER="${QDRANT_CONTAINER:-gutgesagt-qdrant}"
DB_NAME="${DB_NAME:-gutgesagt_app}"
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

# Exakter Vergleich gegen die Namensspalte. "docker ps | grep" traf jeden Teilstring
# der Zeile (Image, Ports) und haette auch einen aehnlich benannten Container gefunden.
container_running() {
    docker ps --format '{{.Names}}' | grep -qxF -- "$1"
}

# Function to log with timestamp
log() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG_FILE"
}

# Vor dem ersten log: tee schreibt nach $BACKUP_ROOT, und ohne das Verzeichnis
# bricht set -e schon beim ersten Logeintrag ab.
mkdir -p "$BACKUP_ROOT"

log "${GREEN}========================================${NC}"
log "${GREEN}Gut gesagt Automated Backup${NC}"
log "${GREEN}========================================${NC}"
log "Backup timestamp: $TIMESTAMP"
log "Day of week: $DAY_OF_WEEK (1=Mon, 7=Sun)"

# Create backup directories
mkdir -p "$DAILY_DIR"
mkdir -p "$WEEKLY_DIR"
mkdir -p "$BACKUP_DIR"

# Check if containers are running
log "\n${YELLOW}Checking Docker containers...${NC}"
if ! container_running "$POSTGRES_CONTAINER"; then
    log "${RED}Error: PostgreSQL container '$POSTGRES_CONTAINER' is not running${NC}"
    exit 1
fi

if ! container_running "$APP_CONTAINER"; then
    log "${RED}Error: Application container '$APP_CONTAINER' is not running${NC}"
    exit 1
fi

if ! container_running "$QDRANT_CONTAINER"; then
    log "${RED}Error: Qdrant container '$QDRANT_CONTAINER' is not running${NC}"
    exit 1
fi

log "All containers are running"

# Backup Qdrant collection
log "\n${YELLOW}Backing up Qdrant collection...${NC}"
docker exec "$APP_CONTAINER" python /app/scripts/backup_qdrant.py \
    --output /backups/daily/backup_$TIMESTAMP/qdrant_snapshot.tar

# Der Snapshot entsteht im Container unter /backups. Ohne den Mount
# $BACKUP_ROOT:/backups am Application-Container bleibt er dort liegen, und auf dem
# Host fehlt er -- dann ist das Backup unvollstaendig und muss laut scheitern.
if [ ! -s "$BACKUP_DIR/qdrant_snapshot.tar" ]; then
    log "${RED}✗ Qdrant backup failed: $BACKUP_DIR/qdrant_snapshot.tar is missing or empty on the host${NC}"
    log "  Is $BACKUP_ROOT mounted at /backups in '$APP_CONTAINER'?"
    exit 1
fi
QDRANT_SIZE=$(du -h "$BACKUP_DIR/qdrant_snapshot.tar" | cut -f1)
log "${GREEN}✓ Qdrant backup completed${NC}"
log "  Size: $QDRANT_SIZE"

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
    ln -s "backup_$TIMESTAMP" "$WEEKLY_DIR/latest"
fi

# Update daily latest symlink
# Relative Ziele: Der Link muss auch im Container unter /backups aufloesen, wo der
# Host-Pfad $BACKUP_ROOT nicht existiert.
rm -f "$DAILY_DIR/latest"
ln -s "backup_$TIMESTAMP" "$DAILY_DIR/latest"

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
log "  cd $(cd "$(dirname "$0")" && pwd)"
log "  ./restore.sh $DAILY_DIR/backup_$TIMESTAMP"
