#!/bin/bash

# Gut gesagt Restore Script
# Runs on HOST system to restore Docker containers data
# Restores from backups in /opt/contentgruen-backups/ on HOST filesystem

set -e  # Exit on error

# Configuration
# Host-Seite des Mounts /backups im Application-Container (wie in backup.sh).
BACKUP_ROOT="${BACKUP_ROOT:-/opt/contentgruen-backups}"
# Containernamen wie in backup.sh: ueberall gleich, abweichend per Umgebung.
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-contentgruen-app-postgres}"
APP_CONTAINER="${APP_CONTAINER:-contentgruen-semantic-search}"
QDRANT_CONTAINER="${QDRANT_CONTAINER:-contentgruen-qdrant}"
DB_NAME="contentgruen_app"
DB_USER="app_user"

# Exakter Vergleich gegen die Namensspalte (siehe backup.sh).
container_running() {
    docker ps --format '{{.Names}}' | grep -qxF -- "$1"
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Gut gesagt Restore System${NC}"
echo -e "${BLUE}========================================${NC}"

# Determine which backup to restore
if [ -n "$1" ]; then
    # Specific backup requested
    BACKUP_DIR="$BACKUP_ROOT/$1"
    # Nur der Zeitstempel angegeben: backup.sh legt die Backups unter daily/ und
    # weekly/ ab, nie direkt unter $BACKUP_ROOT. Daher dort der Reihe nach suchen.
    for SUBDIR in daily weekly; do
        [ -d "$BACKUP_DIR" ] && break
        BACKUP_DIR="$BACKUP_ROOT/$SUBDIR/backup_$1"
    done
    # Nichts gefunden: die Fehlermeldung unten nennt den angegebenen Pfad.
    [ -d "$BACKUP_DIR" ] || BACKUP_DIR="$BACKUP_ROOT/$1"
else
    # backup.sh legt die Backups unter daily/ und weekly/ ab und pflegt dort je
    # einen latest-Link; ein latest direkt unter $BACKUP_ROOT gibt es nicht.
    BACKUP_DIR="$BACKUP_ROOT/daily/latest"
fi

# Validate backup directory
if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${RED}Error: Backup directory not found: $BACKUP_DIR${NC}"
    echo "Available backups:"
    ls -dt "$BACKUP_ROOT"/daily/backup_* "$BACKUP_ROOT"/weekly/backup_* 2>/dev/null | head -10 || echo "No backups found"
    exit 1
fi

# Der Container sieht $BACKUP_ROOT als /backups. Den Pfad dort aus dem Pfad relativ
# zu $BACKUP_ROOT bilden, nach Aufloesen des latest-Links -- basename allein liess
# daily/ bzw. weekly/ weg und ergab bei daily/latest "/backups/latest".
BACKUP_DIR=$(readlink -f "$BACKUP_DIR")
BACKUP_ROOT_REAL=$(readlink -f "$BACKUP_ROOT")
BACKUP_REL="${BACKUP_DIR#"$BACKUP_ROOT_REAL"/}"
if [ "$BACKUP_REL" = "$BACKUP_DIR" ]; then
    echo -e "${RED}Error: $BACKUP_DIR is not below $BACKUP_ROOT_REAL, the container cannot see it${NC}"
    exit 1
fi
CONTAINER_BACKUP_DIR="/backups/$BACKUP_REL"

echo "Restoring from: $BACKUP_DIR"

# Check required files
echo -e "\n${YELLOW}Checking backup files...${NC}"
if [ ! -f "$BACKUP_DIR/qdrant_snapshot.tar" ]; then
    echo -e "${RED}Error: qdrant_snapshot.tar not found in backup${NC}"
    exit 1
fi

if [ ! -f "$BACKUP_DIR/postgresql.sql" ]; then
    echo -e "${RED}Error: postgresql.sql not found in backup${NC}"
    exit 1
fi

if [ -f "$BACKUP_DIR/metadata.json" ]; then
    echo "Metadata file found"
    echo "Backup created: $(grep -o '"created_at": "[^"]*"' "$BACKUP_DIR/metadata.json" | cut -d'"' -f4)"
fi

# Check if containers are running
echo -e "\n${YELLOW}Checking Docker containers...${NC}"
if ! container_running "$POSTGRES_CONTAINER"; then
    echo -e "${RED}Error: PostgreSQL container '$POSTGRES_CONTAINER' is not running${NC}"
    echo "Please start the containers first with: docker-compose up -d"
    exit 1
fi

if ! container_running "$APP_CONTAINER"; then
    echo -e "${RED}Error: Application container '$APP_CONTAINER' is not running${NC}"
    echo "Please start the containers first with: docker-compose up -d"
    exit 1
fi

if ! container_running "$QDRANT_CONTAINER"; then
    echo -e "${RED}Error: Qdrant container '$QDRANT_CONTAINER' is not running${NC}"
    echo "Please start the containers first with: docker-compose up -d"
    exit 1
fi

echo "All containers are running"

# Confirm restore
echo -e "\n${YELLOW}⚠️  WARNING: This will replace all existing data!${NC}"
echo "The following will be restored:"
echo "  - Qdrant collection from: qdrant_snapshot.tar"
echo "  - PostgreSQL database from: postgresql.sql"
echo ""
read -p "Are you sure you want to continue? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
    echo "Restore cancelled"
    exit 0
fi

# Stop application container to prevent writes during restore
echo -e "\n${YELLOW}Stopping application container temporarily...${NC}"
docker stop "$APP_CONTAINER"
echo "Container stopped"

# Restore Qdrant collection
echo -e "\n${YELLOW}Restoring Qdrant collection...${NC}"
docker start "$APP_CONTAINER"
echo "Waiting for application container to start..."
sleep 5

# Wait for container to be ready
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker exec "$APP_CONTAINER" python -c "print('Container ready')" 2>/dev/null; then
        break
    fi
    echo "Waiting for container... ($((RETRY_COUNT+1))/$MAX_RETRIES)"
    sleep 2
    RETRY_COUNT=$((RETRY_COUNT+1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}Error: Container failed to start properly${NC}"
    exit 1
fi

echo "Restoring Qdrant snapshot..."
if docker exec "$APP_CONTAINER" python /app/scripts/restore_qdrant.py \
    --input "$CONTAINER_BACKUP_DIR/qdrant_snapshot.tar"; then
    echo -e "${GREEN}✓ Qdrant restore completed${NC}"
else
    echo -e "${RED}✗ Qdrant restore failed${NC}"
    exit 1
fi

# Stop application container before database restore
echo -e "\n${YELLOW}Stopping application container for database restore...${NC}"
docker stop "$APP_CONTAINER"

# Restore PostgreSQL database (usage tracking metadata)
echo -e "\n${YELLOW}Restoring PostgreSQL database (metadata)...${NC}"
# Der Dump stammt aus pg_dump --clean --create --if-exists und bringt DROP DATABASE,
# CREATE DATABASE und \connect selbst mit. Deshalb gegen die Datenbank postgres
# einspielen: Verbunden mit $DB_NAME scheiterte sein DROP an der offenen Datenbank.
# ON_ERROR_STOP, weil psql Fehler sonst ueberliest und mit 0 endet.
echo "Restoring from backup (drops and recreates $DB_NAME)..."
if docker exec -i "$POSTGRES_CONTAINER" psql -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 -q \
    < "$BACKUP_DIR/postgresql.sql"; then
    echo -e "${GREEN}✓ PostgreSQL restore completed${NC}"
else
    echo -e "${RED}✗ PostgreSQL restore failed${NC}"
    docker start "$APP_CONTAINER"
    exit 1
fi

# Start application container
echo -e "\n${YELLOW}Starting application container...${NC}"
docker start "$APP_CONTAINER"
sleep 5

# Verify restore
echo -e "\n${YELLOW}Verifying restore...${NC}"
echo -n "Checking database connection... "
docker exec "$POSTGRES_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT COUNT(*) FROM usage_tracking;" > /dev/null 2>&1 && echo -e "${GREEN}OK${NC}" || echo -e "${YELLOW}WARNING: Database may be empty${NC}"

echo -n "Checking application health... "
# Das Image hat kein curl, daher python wie im Compose-Healthcheck. Der Start laedt
# das Einbettungsmodell und dauert laenger als die 5 s oben, deshalb bis zu 60 s.
HEALTHY=false
for _ in $(seq 1 30); do
    if docker exec "$APP_CONTAINER" python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/api/v1/health", timeout=5)' > /dev/null 2>&1; then
        HEALTHY=true
        break
    fi
    sleep 2
done
[ "$HEALTHY" = true ] && echo -e "${GREEN}OK${NC}" || echo -e "${YELLOW}WARNING: Health check failed${NC}"

# Summary
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Restore completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Restored from: $BACKUP_DIR"
echo ""
echo "Next steps:"
echo "1. Verify the application is working: http://localhost:8000"
echo "2. Check logs if needed: docker-compose logs -f"
echo ""
echo -e "${YELLOW}Note: Qdrant collection has been restored with all vector embeddings.${NC}"
