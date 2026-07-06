#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "====================================="
echo "Running .NET BFF Tests"
echo "====================================="
echo

cd "$(dirname "$0")/../../backend/BFF"

# Check if .NET SDK is available
if ! command -v dotnet &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} .NET SDK is not installed or not in PATH"
    echo "Please install .NET SDK from https://dotnet.microsoft.com/download"
    exit 1
fi

# Run .NET tests
echo "Running .NET tests..."
dotnet test --no-restore --verbosity quiet

if [ $? -ne 0 ]; then
    echo
    echo -e "${RED}[FAIL]${NC} BFF tests failed!"
    exit 1
else
    echo -e "${GREEN}[OK]${NC} BFF tests passed!"
fi

echo
echo "====================================="
echo "BFF tests completed successfully!"
echo "====================================="
