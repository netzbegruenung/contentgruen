@echo off
echo =====================================
echo Testing ContentGruen Setup
echo =====================================
echo.

REM Test if Docker is available
echo Checking Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Docker is not installed or not in PATH
) else (
    echo [OK] Docker is installed
    docker --version
)

REM Test if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Docker is not running
) else (
    echo [OK] Docker is running
)

echo.

REM Test if .NET is available
echo Checking .NET SDK...
dotnet --version >nul 2>&1
if errorlevel 1 (
    echo [FAIL] .NET SDK is not installed or not in PATH
) else (
    echo [OK] .NET SDK is installed
    dotnet --version
)

echo.

REM Test if Node.js is available
echo Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Node.js is not installed or not in PATH
) else (
    echo [OK] Node.js is installed
    node --version
)

echo.

REM Test if Python is available
echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Python is not installed or not in PATH
) else (
    echo [OK] Python is installed
    python --version
)

echo.

REM Check for port conflicts
echo Checking for port conflicts...
netstat -an | findstr :80 | findstr LISTENING >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Port 80 is in use (Frontend Docker)
)

netstat -an | findstr :4200 | findstr LISTENING >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Port 4200 is in use (Frontend Local)
)

netstat -an | findstr :5054 | findstr LISTENING >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Port 5054 is in use (BFF)
)

netstat -an | findstr :8000 | findstr LISTENING >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Port 8000 is in use (Semantic Search)
)

netstat -an | findstr :5432 | findstr LISTENING >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Port 5432 is in use (PostgreSQL)
)

echo.
echo =====================================
echo Test complete!
echo.
echo To run in Docker mode: run-docker.bat
echo To run in Local mode: run-local.bat
echo =====================================
pause
