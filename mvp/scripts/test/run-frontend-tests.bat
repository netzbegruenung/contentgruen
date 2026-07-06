@echo off
echo =====================================
echo Running Angular Frontend Tests
echo =====================================
echo.

cd /d "%~dp0\..\..\frontend\contentgruen-frontend"

REM Check if node_modules exists
if not exist "node_modules" (
    echo [ERROR] Node modules not found!
    echo Please run: npm install
    exit /b 1
)

REM Run Angular tests in CI mode (no watch, headless Chrome)
echo Running Angular tests in CI mode...
call npm run test:ci

if %ERRORLEVEL% neq 0 (
    echo.
    echo [FAIL] Angular tests failed!
    exit /b %ERRORLEVEL%
) else (
    echo [OK] Angular tests passed!
)

echo.
echo =====================================
echo Frontend tests completed successfully!
echo =====================================
