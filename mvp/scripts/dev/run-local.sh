#!/bin/bash

# Run services locally with only PostgreSQL in Docker
# This script starts PostgreSQL in Docker and runs the other services locally

echo "========================================="
echo "Starting ContentGrün in Local Dev mode"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker first (needed for Qdrant and PostgreSQL).${NC}"
    exit 1
fi

# Navigate to the mvp directory
cd "$(dirname "$0")"

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    # Kill all background processes
    jobs -p | xargs -r kill 2>/dev/null
    # Stop Qdrant and PostgreSQL containers
    docker-compose -f docker-compose.local-dbs.yml down
    exit 0
}

# Trap Ctrl+C and cleanup
trap cleanup INT TERM

# Start Qdrant and PostgreSQL in Docker
echo -e "${GREEN}Starting Qdrant and App PostgreSQL in Docker...${NC}"
docker-compose -f docker-compose.local-dbs.yml up -d

# Wait for services to be ready
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 5

# Check if Qdrant is ready
until curl -f http://localhost:6333/healthz > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo -e "\n${GREEN}Qdrant is ready!${NC}"

# Check if App PostgreSQL is ready
until docker exec contentgruen-app-postgres pg_isready -U app_user > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo -e "${GREEN}App PostgreSQL is ready!${NC}"

# Start Semantic Search Service
echo -e "${BLUE}Starting Semantic Search Service...${NC}"
cd backend/semantic-search-service
if [ -d "venv" ]; then
    echo "Using existing Python virtual environment..."
else
    echo "Creating Python virtual environment..."
    python -m venv venv
fi

# Activate venv and install dependencies
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    source venv/Scripts/activate
else
    # Unix-like
    source venv/bin/activate
fi

pip install -q -r requirements.txt

# Set environment variables for semantic search
export SEMANTIC_SEARCH_QDRANT_URL="http://localhost:6333"
export SEMANTIC_SEARCH_QDRANT_COLLECTION="content_collection"
export APP_DATABASE_URL="postgresql+psycopg2://app_user:changeme@localhost:5433/contentgruen_app"
export SEMANTIC_SEARCH_LOG_LEVEL="DEBUG"
export SEEDING_METADATA_PATH="./metadata"

# Start the semantic search service in background
cd app
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
SEMANTIC_PID=$!
cd ../../..

# Start BFF (.NET)
echo -e "${BLUE}Starting BFF (.NET)...${NC}"
cd backend/BFF

# Set environment variables for BFF
export ASPNETCORE_ENVIRONMENT="Development"
export BACKEND_URL="http://localhost:8000"
export USE_KEYCLOAK="false"
export FRONTEND_URL="http://localhost:4200"

dotnet run &
BFF_PID=$!
cd ../..

# Start Frontend (Angular)
echo -e "${BLUE}Starting Frontend (Angular)...${NC}"
cd frontend/contentgruen-frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Copy local environment configuration
cp src/environments/environment.local.ts src/environments/environment.ts

npm start &
FRONTEND_PID=$!
cd ../..

echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN}All services are starting up...${NC}"
echo -e "${GREEN}====================================${NC}"
echo ""
echo "Frontend: http://localhost:4200/"
echo "BFF: http://localhost:5054/"
echo "Semantic Search API: http://localhost:8000/docs"
echo "Qdrant Dashboard: http://localhost:6333/dashboard"
echo "PostgreSQL (App): localhost:5433"
echo ""
echo "Default login: testuser / Liebe>Hass!"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"

# Wait for all background processes
wait
