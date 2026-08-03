#!/bin/bash

# Test script for ContentGrün backup/restore functionality
# This script verifies that backup and restore work correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}ContentGrün Backup/Restore Test${NC}"
echo -e "${BLUE}========================================${NC}"

# Configuration
BACKUP_DIR="/opt/contentgruen-backups"
TEST_MARKER="TEST_BACKUP_$(date +%Y%m%d_%H%M%S)"
POSTGRES_CONTAINER="contentgruen-app-postgres"
APP_CONTAINER="contentgruen-semantic-search"
QDRANT_CONTAINER="contentgruen-qdrant"

# Function to count Qdrant points
count_qdrant_points() {
    local count=$(curl -s http://localhost:6333/collections/content_collection 2>/dev/null | grep -o '"points_count":[0-9]*' | cut -d':' -f2 2>/dev/null || echo "0")
    echo $count
}

# Function to count PostgreSQL records
count_pg_records() {
    local table=$1
    local count=$(docker exec $POSTGRES_CONTAINER psql -U app_user -d contentgruen_app -t -c "SELECT COUNT(*) FROM $table;" 2>/dev/null || echo "0")
    echo $count
}

# Function to get random content item from Qdrant
get_sample_content() {
    curl -s http://localhost:6333/collections/content_collection/points/scroll -H "Content-Type: application/json" -d '{"limit": 1}' 2>/dev/null | grep -o '"text":"[^"]*"' | head -1 | cut -d'"' -f4
}

echo -e "\n${YELLOW}Step 1: Pre-backup verification${NC}"
echo "Checking current data state..."
INITIAL_CONTENT_COUNT=$(count_qdrant_points)
INITIAL_USAGE_COUNT=$(count_pg_records "usage_tracking")
SAMPLE_CONTENT=$(get_sample_content)

echo "Initial state:"
echo "  - Content items (Qdrant): $INITIAL_CONTENT_COUNT"
echo "  - Usage tracking records: $INITIAL_USAGE_COUNT"
echo "  - Sample content: $(echo $SAMPLE_CONTENT | head -c 50)..."

if [ "$INITIAL_CONTENT_COUNT" -eq "0" ]; then
    echo -e "${YELLOW}Warning: Qdrant collection is empty. Please seed some data first.${NC}"
    echo "Run the application and add some content before testing backup/restore."
    exit 1
fi

echo -e "\n${YELLOW}Step 2: Create backup${NC}"
echo "Running backup script..."
./backup.sh

# Check if backup was created
LATEST_BACKUP=$(readlink -f "$BACKUP_DIR/latest")
if [ ! -d "$LATEST_BACKUP" ]; then
    echo -e "${RED}Error: Backup was not created${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Backup created at: $LATEST_BACKUP${NC}"

# Verify backup files
echo -e "\n${YELLOW}Step 3: Verify backup files${NC}"
for file in qdrant_snapshot.tar postgresql.sql metadata.json; do
    if [ -f "$LATEST_BACKUP/$file" ]; then
        SIZE=$(du -h "$LATEST_BACKUP/$file" | cut -f1)
        echo -e "${GREEN}✓ $file exists (size: $SIZE)${NC}"
    else
        echo -e "${RED}✗ $file missing${NC}"
        exit 1
    fi
done

echo -e "\n${YELLOW}Step 4: Simulate data change${NC}"
echo "Adding test marker to Qdrant..."
# Use Qdrant API to add a test point
TEST_ID=$(uuidgen 2>/dev/null || echo "00000000-0000-0000-0000-$(date +%s)")
# Generate random vector using container's Python (not host Python)
RANDOM_VECTOR=$(docker exec $APP_CONTAINER python -c "import random; print([random.random() for _ in range(768)])")
curl -X PUT "http://localhost:6333/collections/content_collection/points" \
  -H "Content-Type: application/json" \
  -d "{
    \"points\": [{
      \"id\": \"$TEST_ID\",
      \"vector\": $RANDOM_VECTOR,
      \"payload\": {
        \"text\": \"$TEST_MARKER\",
        \"content_type\": \"generic_text\"
      }
    }]
  }" 2>/dev/null || true

echo "Test marker added with ID: $TEST_ID"

echo -e "\n${YELLOW}Step 5: Restore from backup${NC}"
echo "Running restore script..."
echo "yes" | ./restore.sh

echo -e "\n${YELLOW}Step 6: Post-restore verification${NC}"
echo "Checking restored data state..."

# Wait for services to stabilize
sleep 10

RESTORED_CONTENT_COUNT=$(count_qdrant_points)
RESTORED_USAGE_COUNT=$(count_pg_records "usage_tracking")
RESTORED_SAMPLE=$(get_sample_content)

# Check if test marker is gone (should not be in restored data)
TEST_MARKER_PRESENT=$(curl -s "http://localhost:6333/collections/content_collection/points/scroll" \
  -H "Content-Type: application/json" \
  -d "{\"filter\": {\"must\": [{\"key\": \"text\", \"match\": {\"value\": \"$TEST_MARKER\"}}]}}" 2>/dev/null \
  | grep -c "$TEST_MARKER" 2>/dev/null || echo "0")
TEST_MARKER_PRESENT=$(echo "$TEST_MARKER_PRESENT" | tr -d '\n\r ')

echo "Restored state:"
echo "  - Content items (Qdrant): $RESTORED_CONTENT_COUNT (original: $INITIAL_CONTENT_COUNT)"
echo "  - Usage tracking records: $RESTORED_USAGE_COUNT (original: $INITIAL_USAGE_COUNT)"
echo "  - Test marker present: $TEST_MARKER_PRESENT (should be 0)"

# Verify restoration
echo -e "\n${YELLOW}Step 7: Test results${NC}"
TESTS_PASSED=0
TESTS_FAILED=0

# Test 1: Content count matches
if [ "$RESTORED_CONTENT_COUNT" -eq "$INITIAL_CONTENT_COUNT" ]; then
    echo -e "${GREEN}✓ Content count restored correctly${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Content count mismatch${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 2: Usage tracking count matches
if [ "$RESTORED_USAGE_COUNT" -eq "$INITIAL_USAGE_COUNT" ]; then
    echo -e "${GREEN}✓ Usage tracking count restored correctly${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Usage tracking count mismatch${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 3: Test marker removed (data properly restored)
if [ "$TEST_MARKER_PRESENT" -eq "0" ]; then
    echo -e "${GREEN}✓ Test marker removed (proper restore)${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Test marker still present${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 4: API health check (with retries)
echo -n "Waiting for API to be ready"
API_HEALTH="0"
MAX_RETRIES=30
RETRY_COUNT=0
while [ "$RETRY_COUNT" -lt "$MAX_RETRIES" ]; do
    API_HEALTH=$(docker exec $APP_CONTAINER curl -s http://localhost:8000/api/v1/test 2>/dev/null | grep -c "ok" 2>/dev/null || echo "0")
    API_HEALTH=$(echo "$API_HEALTH" | tr -d '\n\r ')
    if [ "$API_HEALTH" -gt "0" ]; then
        break
    fi
    echo -n "."
    sleep 2
    RETRY_COUNT=$((RETRY_COUNT + 1))
done
echo ""

if [ "$API_HEALTH" -gt "0" ]; then
    echo -e "${GREEN}✓ API is healthy${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ API health check failed after ${MAX_RETRIES} retries${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Summary
echo -e "\n${BLUE}========================================${NC}"
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ($TESTS_PASSED/$((TESTS_PASSED + TESTS_FAILED)))${NC}"
    echo -e "${GREEN}Backup/Restore system is working correctly.${NC}"
else
    echo -e "${RED}Some tests failed! ($TESTS_FAILED failed, $TESTS_PASSED passed)${NC}"
    echo -e "${RED}Please check the logs for details.${NC}"
fi
echo -e "${BLUE}========================================${NC}"

# Cleanup
echo -e "\n${YELLOW}Cleaning up test backup...${NC}"
# Keep the backup for manual inspection if needed
echo "Test backup kept at: $LATEST_BACKUP"
echo "To remove it manually: rm -rf $LATEST_BACKUP"
