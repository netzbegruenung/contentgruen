@echo off
echo =========================================
echo Starting ContentGruen in Local Dev mode
echo =========================================

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not running. Please start Docker Desktop first ^(needed for Qdrant and PostgreSQL^).
    pause
    exit /b 1
)

REM Navigate to the mvp directory (two levels up from scripts/dev/)
cd /d "%~dp0..\.."

REM Start Qdrant and App PostgreSQL in Docker
echo Starting Qdrant and App PostgreSQL in Docker...
docker-compose -f docker-compose.local-dbs.yml up -d

REM Wait for services to be ready
echo Waiting for services to be ready...
timeout /t 5 /nobreak >nul

REM Check if Qdrant is ready
:wait_qdrant
curl -f http://localhost:6333/healthz >nul 2>&1
if errorlevel 1 (
    echo Waiting for Qdrant...
    timeout /t 2 /nobreak >nul
    goto wait_qdrant
)
echo Qdrant is ready!

REM Check if app PostgreSQL is ready
:wait_postgres_app
docker exec contentgruen-app-postgres pg_isready -U app_user >nul 2>&1
if errorlevel 1 (
    echo Waiting for App PostgreSQL...
    timeout /t 2 /nobreak >nul
    goto wait_postgres_app
)
echo App PostgreSQL is ready!

REM Start three command windows for each service
echo.
echo Starting services in separate windows...
echo.

REM Start Semantic Search Service
start "Semantic Search Service" cmd /k "cd backend\semantic-search-service && (if not exist venv python -m venv venv) && call venv\Scripts\activate.bat && pip install -q -r requirements.txt && set SEMANTIC_SEARCH_QDRANT_URL=http://localhost:6333 && set SEMANTIC_SEARCH_QDRANT_COLLECTION=content_collection && set \"APP_DATABASE_URL=postgresql+psycopg2://app_user:changeme@localhost:5433/contentgruen_app\" && set SEMANTIC_SEARCH_LOG_LEVEL=DEBUG && set SEEDING_METADATA_PATH=metadata && cd app && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

REM Wait a bit for semantic search to start
timeout /t 3 /nobreak >nul

REM Start BFF
start "BFF - .NET" cmd /k "cd backend\BFF && set ASPNETCORE_ENVIRONMENT=Development && set BACKEND_URL=http://localhost:8000 && set USE_KEYCLOAK=false && set FRONTEND_URL=http://localhost:4200 && dotnet run"

REM Wait a bit for BFF to start
timeout /t 3 /nobreak >nul

REM Copy local environment configuration
copy frontend\contentgruen-frontend\src\environments\environment.local.ts frontend\contentgruen-frontend\src\environments\environment.ts >nul

REM Start Frontend
start "Frontend - Angular" cmd /k "cd frontend\contentgruen-frontend && (if not exist node_modules npm install) && npm start"

echo.
echo ====================================
echo All services are starting up...
echo ====================================
echo.
echo Frontend: http://localhost:4200/
echo BFF: http://localhost:5054/
echo Semantic Search API: http://localhost:8000/docs
echo Qdrant Dashboard: http://localhost:6333/dashboard
echo PostgreSQL (App): localhost:5433
echo.
echo Default login: testuser / Liebe^>Hass!
echo.
echo To stop services:
echo 1. Close all the service windows
echo 2. Run: docker-compose -f docker-compose.local-dbs.yml down
echo.
pause
