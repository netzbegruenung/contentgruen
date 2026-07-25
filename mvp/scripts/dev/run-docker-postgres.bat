@echo off
echo =====================================
echo Starting local databases (Qdrant + PostgreSQL)
echo =====================================
echo.

cd /d "%~dp0\..\.."

echo Starting database containers...
docker compose -f docker-compose.local-dbs.yml up -d

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to start the databases
    exit /b 1
)

echo.
echo Qdrant is running on port 6333
echo PostgreSQL is running on port 5433
echo Connection string: postgresql://app_user:changeme@localhost:5433/contentgruen_app
echo.
echo To stop: docker compose -f docker-compose.local-dbs.yml down
echo To reset: docker compose -f docker-compose.local-dbs.yml down -v
echo =====================================
