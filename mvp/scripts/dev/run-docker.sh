#!/bin/bash

# Run everything in Docker using docker-compose.dev.yml
# This script starts all services in Docker containers

echo "====================================="
echo "Starting ContentGrün in Docker mode"
echo "====================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Navigate to the mvp directory
cd "$(dirname "$0")"

# Stop any running containers
echo -e "${YELLOW}Stopping any existing containers...${NC}"
docker-compose -f docker-compose.dev.yml down

# Build and start all services
echo -e "${GREEN}Building and starting all services...${NC}"
docker-compose -f docker-compose.dev.yml up --build

echo -e "${GREEN}Services are starting up...${NC}"
echo "Frontend: http://localhost/"
echo "BFF: http://localhost:5054/"
echo "Semantic Search API: http://localhost:8000/docs"
echo "PostgreSQL: localhost:5432"
echo ""
echo "Default login: testuser / Liebe>Hass!"
echo ""
echo "Press Ctrl+C to stop all services"
