#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "====================================="
echo "Installing ContentGruen Dependencies"
echo "====================================="
echo

cd "$(dirname "$0")/../.."

# Install Python dependencies
echo "[1/3] Installing Python dependencies..."
echo "-------------------------------------"
cd backend/semantic-search-service
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv || python -m venv venv
fi
echo "Installing Python packages..."
if [ -f "venv/bin/pip" ]; then
    venv/bin/pip install -r requirements.txt
else
    venv/Scripts/pip install -r requirements.txt
fi
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERROR]${NC} Failed to install Python dependencies"
    exit 1
fi
echo -e "${GREEN}[OK]${NC} Python dependencies installed"
cd ../..
echo

# Install .NET dependencies
echo "[2/3] Installing .NET dependencies..."
echo "-------------------------------------"
cd backend/BFF
dotnet restore
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERROR]${NC} Failed to install .NET dependencies"
    exit 1
fi
echo -e "${GREEN}[OK]${NC} .NET dependencies installed"
cd ../..
echo

# Install Node.js dependencies
echo "[3/3] Installing Node.js dependencies..."
echo "-------------------------------------"
cd frontend/contentgruen-frontend
npm install
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERROR]${NC} Failed to install Node.js dependencies"
    exit 1
fi
echo -e "${GREEN}[OK]${NC} Node.js dependencies installed"
cd ../..
echo

echo "====================================="
echo "All dependencies installed successfully!"
echo "====================================="
