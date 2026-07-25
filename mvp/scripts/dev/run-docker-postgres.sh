#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "====================================="
echo "Starting PostgreSQL with pgvector"
echo "====================================="
echo

cd "$(dirname "$0")/../.."

echo "Starting PostgreSQL container..."
docker-compose -f docker-compose.postgres.yml up -d

if [ $? -ne 0 ]; then
    echo -e "${RED}[ERROR]${NC} Failed to start PostgreSQL"
    exit 1
fi

echo
echo -e "${GREEN}PostgreSQL is running on port 5432${NC}"
echo "Connection string: postgresql://semantic_search:semantic_search@localhost:5432/semantic_search"
echo
echo "To stop: docker-compose -f docker-compose.postgres.yml down"
echo "To reset: docker-compose -f docker-compose.postgres.yml down -v"
echo "====================================="
