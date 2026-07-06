@echo off
echo =====================================
echo Switching to Local Environment Configuration
echo =====================================
echo.

cd /d "%~dp0\..\..\frontend\contentgruen-frontend\src\environments"

REM Switch to local configuration
(
echo export const environment = {
echo   production: false,
echo   baseUrl: 'http://localhost:5054',
echo   clientId: 'contentgruen',
echo   mockAuth: true
echo };
) > environment.ts

echo [OK] environment.ts has been set to local configuration
echo.
echo Configuration:
echo - baseUrl: 'http://localhost:5054' (direct BFF connection)
echo - mockAuth: true (dummy authentication)
echo.
echo =====================================
echo Switch complete!
echo =====================================
