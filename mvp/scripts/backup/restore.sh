#!/bin/bash

# ContentGrün Restore Script
# Runs on HOST system to restore Docker containers data
# Restores from backups in /opt/contentgruen-backups/ on HOST filesystem

set -e  # Exit on error

# Configuration
BACKUP_ROOT="/opt/contentgruen-backups"
POSTGRES_CONTAINER="contentgruen-app-postgres"
APP_CONTAINER="contentgruen-semantic-search"
QDRANT_CONTAINER="contentgruen-qdrant"
DB_NAME="contentgruen_app"
DB_USER="app_user"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}ContentGrün Restore System${NC}"
echo -e "${BLUE}========================================${NC}"

# Determine which backup to restore
if [ -n "$1" ]; then
    # Specific backup requested
    BACKUP_DIR="$BACKUP_ROOT/$1"
    if [ ! -d "$BACKUP_DIR" ]; then
        # Try without backup_ prefix
        BACKUP_DIR="$BACKUP_ROOT/backup_$1"
    fi
else
    # Use latest backup
    if [ -L "$BACKUP_ROOT/latest" ]; then
        BACKUP_DIR=$(readlink -f "$BACKUP_ROOT/latest")
    else
        # Find most recent backup
        BACKUP_DIR=$(ls -dt "$BACKUP_ROOT"/backup_* 2>/dev/null | head -1)
    fi
fi

# Validate backup directory
if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${RED}Error: Backup directory not found: $BACKUP_DIR${NC}"
    echo "Available backups:"
    ls -dt "$BACKUP_ROOT"/backup_* 2>/dev/null | head -10 || echo "No backups found"
    exit 1
fi

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
if ! docker ps | grep -q "$POSTGRES_CONTAINER"; then
    echo -e "${RED}Error: PostgreSQL container '$POSTGRES_CONTAINER' is not running${NC}"
    echo "Please start the containers first with: docker-compose up -d"
    exit 1
fi

if ! docker ps | grep -q "$APP_CONTAINER"; then
    echo -e "${RED}Error: Application container '$APP_CONTAINER' is not running${NC}"
    echo "Please start the containers first with: docker-compose up -d"
    exit 1
fi

if ! docker ps | grep -q "$QDRANT_CONTAINER"; then
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
docker exec "$APP_CONTAINER" python /app/scripts/restore_qdrant.py \
    --input /backups/$(basename "$BACKUP_DIR")/qdrant_snapshot.tar

if [ $? -eq 0 ]; then
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
echo "Dropping existing database..."
docker exec "$POSTGRES_CONTAINER" psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;" || true

echo "Creating fresh database..."
docker exec "$POSTGRES_CONTAINER" psql -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;"

echo "Restoring from backup..."
docker exec -i "$POSTGRES_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_DIR/postgresql.sql"

if [ $? -eq 0 ]; then
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
docker exec "$APP_CONTAINER" curl -s http://localhost:8000/api/v1/test > /dev/null 2>&1 && echo -e "${GREEN}OK${NC}" || echo -e "${YELLOW}WARNING: Health check failed${NC}"

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
