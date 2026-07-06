@echo off
echo =========================================
echo Stopping ContentGruen Local Development
echo =========================================

REM Kill the service windows by their title
echo Stopping service windows...
taskkill /F /FI "WINDOWTITLE eq Semantic Search Service*" 2>nul
taskkill /F /FI "WINDOWTITLE eq BFF - .NET*" 2>nul
taskkill /F /FI "WINDOWTITLE eq Frontend - Angular*" 2>nul

REM Stop database containers (Qdrant + PostgreSQL)
echo Stopping Qdrant and PostgreSQL databases...
cd /d "%~dp0..\.."
docker-compose -f docker-compose.local-dbs.yml down

REM Clean up any orphaned Python/Node processes
echo Cleaning up any orphaned processes...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM node.exe 2>nul
taskkill /F /IM dotnet.exe 2>nul

echo.
echo ====================================
echo All services stopped successfully!
echo ====================================
echo.
pause
