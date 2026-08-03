#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "====================================="
echo "Testing ContentGruen Setup"
echo "====================================="
echo

# Test if Docker is available
echo "Checking Docker..."
if command -v docker &> /dev/null; then
    echo -e "${GREEN}[OK]${NC} Docker is installed"
    docker --version
else
    echo -e "${RED}[FAIL]${NC} Docker is not installed or not in PATH"
fi

# Test if Docker is running
if docker info &> /dev/null; then
    echo -e "${GREEN}[OK]${NC} Docker is running"
else
    echo -e "${RED}[FAIL]${NC} Docker is not running"
fi

echo

# Test if .NET is available
echo "Checking .NET SDK..."
if command -v dotnet &> /dev/null; then
    echo -e "${GREEN}[OK]${NC} .NET SDK is installed"
    dotnet --version
else
    echo -e "${RED}[FAIL]${NC} .NET SDK is not installed or not in PATH"
fi

echo

# Test if Node.js is available
echo "Checking Node.js..."
if command -v node &> /dev/null; then
    echo -e "${GREEN}[OK]${NC} Node.js is installed"
    node --version
else
    echo -e "${RED}[FAIL]${NC} Node.js is not installed or not in PATH"
fi

echo

# Test if Python is available
echo "Checking Python..."
if command -v python3 &> /dev/null; then
    echo -e "${GREEN}[OK]${NC} Python is installed"
    python3 --version
elif command -v python &> /dev/null; then
    echo -e "${GREEN}[OK]${NC} Python is installed"
    python --version
else
    echo -e "${RED}[FAIL]${NC} Python is not installed or not in PATH"
fi

echo

# Check for port conflicts
echo "Checking for port conflicts..."

check_port() {
    local port=$1
    local service=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}[WARNING]${NC} Port $port is in use ($service)"
    fi
}

check_port 80 "Frontend Docker"
check_port 4200 "Frontend Local"
check_port 5054 "BFF"
check_port 8000 "Semantic Search"
check_port 5432 "PostgreSQL"

echo
echo "====================================="
echo "Test complete!"
echo
echo "To run in Docker mode: ./scripts/dev/run-docker.sh"
echo "To run in Local mode: ./scripts/dev/run-local.sh"
echo "====================================="
