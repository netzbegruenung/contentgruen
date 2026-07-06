#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "====================================="
echo "Running Angular Frontend Tests"
echo "====================================="
echo

cd "$(dirname "$0")/../../frontend/contentgruen-frontend"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${RED}[ERROR]${NC} Node modules not found!"
    echo "Please run: npm install"
    exit 1
fi

# Run Angular tests in CI mode (no watch, headless Chrome)
echo "Running Angular tests in CI mode..."
npm run test:ci

if [ $? -ne 0 ]; then
    echo
    echo -e "${RED}[FAIL]${NC} Angular tests failed!"
    exit 1
else
    echo -e "${GREEN}[OK]${NC} Angular tests passed!"
fi

echo
echo "====================================="
echo "Frontend tests completed successfully!"
echo "====================================="
