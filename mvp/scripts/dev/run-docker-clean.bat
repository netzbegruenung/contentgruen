@echo off
echo =====================================
echo Clean rebuild (no cache) - SLOW!
echo =====================================
echo This will take ~10 minutes. Use run-docker.bat for fast builds.
echo.
pause

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

REM Navigate to the mvp directory (scripts/dev -> mvp)
cd /d "%~dp0..\.."

REM Stop and remove everything
echo Stopping and removing all containers, images, and cache...
docker-compose -f docker-compose.dev.yml down --rmi all --volumes

REM Build from scratch (no cache)
echo Building from scratch (no cache)...
docker-compose -f docker-compose.dev.yml build --no-cache

REM Start services
echo Starting services...
docker-compose -f docker-compose.dev.yml up

echo.
echo Services are available at:
echo Frontend: http://localhost/
echo BFF: http://localhost:5054/
echo Semantic Search API: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop all services
pause
