#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "====================================="
echo "Cleaning ContentGruen Development Environment"
echo "====================================="
echo
echo -e "${YELLOW}WARNING: This will remove all generated files,"
echo -e "         dependencies, and Docker volumes!${NC}"
echo
echo "Press Ctrl+C to cancel or Enter to continue..."
read

cd "$(dirname "$0")/../.."

# Stop and remove Docker containers
echo "Stopping Docker containers..."
docker-compose -f docker-compose.dev.yml down -v 2>/dev/null
docker-compose -f docker-compose.local-dbs.yml down -v 2>/dev/null
docker-compose -f docker-compose.tst.yml down -v 2>/dev/null

# Clean Python environment
echo "Cleaning Python environment..."
if [ -d "backend/semantic-search-service/venv" ]; then
    rm -rf backend/semantic-search-service/venv
    echo -e "${GREEN}[OK]${NC} Python venv removed"
fi
find backend/semantic-search-service -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
if [ -d "backend/semantic-search-service/metadata" ]; then
    rm -rf backend/semantic-search-service/metadata
    echo -e "${GREEN}[OK]${NC} Metadata directory removed"
fi

# Clean .NET build artifacts
echo "Cleaning .NET build artifacts..."
if [ -d "backend/BFF/bin" ]; then
    rm -rf backend/BFF/bin
fi
if [ -d "backend/BFF/obj" ]; then
    rm -rf backend/BFF/obj
fi
echo -e "${GREEN}[OK]${NC} .NET artifacts removed"

# Clean Node.js dependencies and build
echo "Cleaning Node.js environment..."
if [ -d "frontend/contentgruen-frontend/node_modules" ]; then
    rm -rf frontend/contentgruen-frontend/node_modules
    echo -e "${GREEN}[OK]${NC} node_modules removed"
fi
if [ -d "frontend/contentgruen-frontend/dist" ]; then
    rm -rf frontend/contentgruen-frontend/dist
    echo -e "${GREEN}[OK]${NC} dist directory removed"
fi
if [ -d "frontend/contentgruen-frontend/.angular" ]; then
    rm -rf frontend/contentgruen-frontend/.angular
    echo -e "${GREEN}[OK]${NC} .angular cache removed"
fi

echo
echo "====================================="
echo "Clean complete!"
echo
echo "Run scripts/setup/install-dependencies.sh to reinstall"
echo "====================================="
