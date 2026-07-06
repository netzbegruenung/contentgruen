@echo off
echo =====================================
echo Starting PostgreSQL with pgvector
echo =====================================
echo.

cd /d "%~dp0\..\.."

echo Starting PostgreSQL container...
docker-compose -f docker-compose.postgres.yml up -d

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to start PostgreSQL
    exit /b 1
)

echo.
echo PostgreSQL is running on port 5432
echo Connection string: postgresql://semantic_search:semantic_search@localhost:5432/semantic_search
echo.
echo To stop: docker-compose -f docker-compose.postgres.yml down
echo To reset: docker-compose -f docker-compose.postgres.yml down -v
echo =====================================
