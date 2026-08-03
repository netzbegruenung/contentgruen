#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "====================================="
echo "Running All ContentGruen Tests"
echo "====================================="
echo

TESTS_FAILED=0
SCRIPT_DIR="$(dirname "$0")"

# Run Python backend tests
echo "[1/3] Running Python Backend Tests..."
echo "-------------------------------------"
"$SCRIPT_DIR/run-backend-tests.sh"
if [ $? -ne 0 ]; then
    TESTS_FAILED=1
    echo -e "${RED}[FAIL]${NC} Python tests failed!"
else
    echo -e "${GREEN}[OK]${NC} Python tests passed!"
fi
echo

# Run Angular frontend tests
echo "[2/3] Running Angular Frontend Tests..."
echo "-------------------------------------"
"$SCRIPT_DIR/run-frontend-tests.sh"
if [ $? -ne 0 ]; then
    TESTS_FAILED=1
    echo -e "${RED}[FAIL]${NC} Angular tests failed!"
else
    echo -e "${GREEN}[OK]${NC} Angular tests passed!"
fi
echo

# Run .NET BFF tests
echo "[3/3] Running .NET BFF Tests..."
echo "-------------------------------------"
"$SCRIPT_DIR/run-bff-tests.sh"
if [ $? -ne 0 ]; then
    TESTS_FAILED=1
    echo -e "${RED}[FAIL]${NC} BFF tests failed!"
else
    echo -e "${GREEN}[OK]${NC} BFF tests passed!"
fi
echo

# Summary
echo "====================================="
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}SUCCESS: All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}FAILURE: Some tests failed!${NC}"
    exit 1
fi
