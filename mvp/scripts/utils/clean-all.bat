@echo off
echo =====================================
echo Cleaning ContentGruen Development Environment
echo =====================================
echo.
echo WARNING: This will remove all generated files,
echo          dependencies, and Docker volumes!
echo.
echo Press Ctrl+C to cancel or
pause

cd /d "%~dp0\..\.."

REM Stop and remove Docker containers
echo Stopping Docker containers...
docker-compose -f docker-compose.dev.yml down -v 2>nul
docker-compose -f docker-compose.local-dbs.yml down -v 2>nul
docker-compose -f docker-compose.tst.yml down -v 2>nul

REM Clean Python environment
echo Cleaning Python environment...
if exist "backend\semantic-search-service\venv" (
    rmdir /s /q "backend\semantic-search-service\venv"
    echo [OK] Python venv removed
)
if exist "backend\semantic-search-service\__pycache__" (
    rmdir /s /q "backend\semantic-search-service\__pycache__"
)
if exist "backend\semantic-search-service\app\__pycache__" (
    rmdir /s /q "backend\semantic-search-service\app\__pycache__"
)
if exist "backend\semantic-search-service\metadata" (
    rmdir /s /q "backend\semantic-search-service\metadata"
    echo [OK] Metadata directory removed
)

REM Clean .NET build artifacts
echo Cleaning .NET build artifacts...
if exist "backend\BFF\bin" (
    rmdir /s /q "backend\BFF\bin"
)
if exist "backend\BFF\obj" (
    rmdir /s /q "backend\BFF\obj"
)
echo [OK] .NET artifacts removed

REM Clean Node.js dependencies and build
echo Cleaning Node.js environment...
if exist "frontend\contentgruen-frontend\node_modules" (
    rmdir /s /q "frontend\contentgruen-frontend\node_modules"
    echo [OK] node_modules removed
)
if exist "frontend\contentgruen-frontend\dist" (
    rmdir /s /q "frontend\contentgruen-frontend\dist"
    echo [OK] dist directory removed
)
if exist "frontend\contentgruen-frontend\.angular" (
    rmdir /s /q "frontend\contentgruen-frontend\.angular"
    echo [OK] .angular cache removed
)

echo.
echo =====================================
echo Clean complete!
echo.
echo Run scripts/setup/install-dependencies.bat to reinstall
echo =====================================
