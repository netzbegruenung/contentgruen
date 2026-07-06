#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "====================================="
echo "Running Semantic Search Service Tests"
echo "====================================="
echo

cd "$(dirname "$0")/../../backend/semantic-search-service"

# Check if venv exists
if [ -f "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
elif [ -f "venv/Scripts/python.exe" ]; then
    PYTHON="venv/Scripts/python.exe"
else
    echo -e "${RED}[ERROR]${NC} Virtual environment not found!"
    echo "Please run: python -m venv venv"
    echo "Then: venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Run unit tests (excluding seeding implementation which requires special setup)
echo "Running unit tests..."
$PYTHON -m pytest app/tests/unit/ --ignore=app/tests/unit/services/test_seeding_implementation.py --tb=short -q

if [ $? -ne 0 ]; then
    echo
    echo -e "${RED}[FAIL]${NC} Unit tests failed!"
    exit 1
else
    echo -e "${GREEN}[OK]${NC} Unit tests passed!"
fi

echo
echo "====================================="
echo "Backend tests completed successfully!"
echo "====================================="
