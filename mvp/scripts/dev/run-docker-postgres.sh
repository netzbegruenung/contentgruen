#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "====================================="
echo "Starting local databases (Qdrant + PostgreSQL)"
echo "====================================="
echo

cd "$(dirname "$0")/../.."

echo "Starting database containers..."
docker compose -f docker-compose.local-dbs.yml up -d

if [ $? -ne 0 ]; then
    echo -e "${RED}[ERROR]${NC} Failed to start the databases"
    exit 1
fi

echo
echo -e "${GREEN}Qdrant is running on port 6333${NC}"
echo -e "${GREEN}PostgreSQL is running on port 5433${NC}"
echo "Connection string: postgresql://app_user:changeme@localhost:5433/contentgruen_app"
echo
echo "To stop: docker compose -f docker-compose.local-dbs.yml down"
echo "To reset: docker compose -f docker-compose.local-dbs.yml down -v"
echo "====================================="
