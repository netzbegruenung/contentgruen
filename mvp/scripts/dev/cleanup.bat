@echo off
echo =========================================
echo Cleaning up ContentGruen Development Environment
echo =========================================

REM Kill any local Python/Node processes that might be running
echo Stopping any local processes...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM node.exe 2>nul
taskkill /F /IM uvicorn.exe 2>nul

REM Stop all Docker containers
echo Stopping Docker containers...
docker-compose -f docker-compose.dev.yml down 2>nul
docker-compose -f docker-compose.local-dbs.yml down 2>nul
docker-compose -f docker-compose.tst.yml down 2>nul

REM Kill any orphaned cmd windows
echo Closing any orphaned command windows...
taskkill /F /FI "WINDOWTITLE eq Semantic Search Service*" 2>nul
taskkill /F /FI "WINDOWTITLE eq BFF - .NET*" 2>nul
taskkill /F /FI "WINDOWTITLE eq Frontend - Angular*" 2>nul

echo.
echo ====================================
echo Cleanup complete!
echo ====================================
echo.
echo You can now start fresh with either:
echo   - docker-compose -f docker-compose.dev.yml up (Recommended)
echo   - run-docker.bat
echo.
pause
