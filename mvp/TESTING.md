# Testing Guide for ContentGrün

## Quick Test Commands

### Run All Tests
```bash
# Windows - from mvp directory
run-tests.bat
# Or: scripts/test/run-all-tests.bat

# Unix/Linux/Mac - from mvp directory
./run-tests.sh
# Or: scripts/test/run-all-tests.sh

# Run individual test suites:
scripts/test/run-backend-tests.bat   # Python tests
scripts/test/run-frontend-tests.bat  # Angular tests
scripts/test/run-bff-tests.bat       # .NET tests
```

## Python Backend Tests

### Location
`mvp/backend/semantic-search-service/app/tests/`

### Run Tests
```bash
# From mvp directory
scripts/test/run-backend-tests.bat

# Or manually with virtual environment
cd backend/semantic-search-service
./venv/Scripts/python.exe -m pytest app/tests/unit/ --ignore=app/tests/unit/services/test_seeding_implementation.py --tb=short -q
```

### Why we ignore test_seeding_implementation.py
This test requires special database setup and is meant for integration testing environments.

## Angular Frontend Tests

### Location
`mvp/frontend/contentgruen-frontend/src/app/`

### Run Tests
```bash
# From mvp directory
scripts/test/run-frontend-tests.bat

# Or manually
cd frontend/contentgruen-frontend
npm run test:ci
```

## Pre-commit Hook

Tests are automatically run before commits via `.pre-commit-config.yaml`. The hook:
1. Runs Python unit tests (excluding seeding implementation)
2. Formats Python code with Black
3. Checks for trailing whitespace and other issues

## Common Issues and Solutions

### Issue: Python tests fail with "No module named 'core'"
**Solution**: Tests must be run from `semantic-search-service` directory with venv Python:
```bash
cd mvp/backend/semantic-search-service
./venv/Scripts/python.exe -m pytest app/tests/
```

### Issue: Angular tests hang or require interaction
**Solution**: Angular 20+ runs tests interactively by default. Use CI mode or close manually.

### Issue: Virtual environment not found
**Solution**: Create and setup the virtual environment:
```bash
cd mvp/backend/semantic-search-service
python -m venv venv
./venv/Scripts/pip install -r requirements.txt
```

## Test Coverage

- **Python Backend**: 188 unit tests covering repositories and services
- **Angular Frontend**: Component and service tests
- **Integration Tests**: Require database setup (not run in pre-commit)

## Docker Testing

For full integration testing in Docker environment:
```bash
cd mvp
./run-docker.bat
# Then run tests inside containers if needed
```
