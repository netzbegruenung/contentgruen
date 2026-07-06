@echo off
echo =====================================
echo Running Semantic Search Service Tests
echo =====================================
echo.

cd /d "%~dp0\..\..\backend\semantic-search-service"

REM Check if venv exists
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then: venv\Scripts\pip install -r requirements.txt
    exit /b 1
)

REM Run unit tests (excluding seeding implementation which requires special setup)
echo Running unit tests...
venv\Scripts\python.exe -m pytest app/tests/unit/ --ignore=app/tests/unit/services/test_seeding_implementation.py --tb=short -q

if %ERRORLEVEL% neq 0 (
    echo.
    echo [FAIL] Unit tests failed!
    exit /b %ERRORLEVEL%
) else (
    echo [OK] Unit tests passed!
)

echo.
echo =====================================
echo Backend tests completed successfully!
echo =====================================
