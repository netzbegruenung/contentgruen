@echo off
echo =====================================
echo Starting ContentGruen in Docker mode
echo (Using Docker cache for fast builds)
echo =====================================
echo.
echo FAST MODE: Uses cached layers - only rebuilds what changed
echo For clean rebuild (slow): run-docker-clean.bat
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

REM Navigate to the mvp directory (scripts/dev -> mvp)
cd /d "%~dp0..\.."

REM Stop any running containers
echo Stopping any existing containers...
docker-compose -f docker-compose.dev.yml down

REM Build and start all services
REM Uses Docker layer caching - only rebuilds changed layers
echo Building and starting all services...
docker-compose -f docker-compose.dev.yml up --build

echo.
echo Services are available at:
echo Frontend: http://localhost/
echo BFF: http://localhost:5054/
echo Semantic Search API: http://localhost:8000/docs
echo PostgreSQL (Semantic): localhost:5432
echo PostgreSQL (App): localhost:5433
echo.
echo Default login: testuser / Liebe^>Hass!
echo.
echo Press Ctrl+C to stop all services
pause
