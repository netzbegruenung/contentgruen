@echo off
echo Resetting environment configuration to Docker mode...

REM Reset frontend environment to Docker mode (empty baseUrl)
echo export const environment = { > frontend\contentgruen-frontend\src\environments\environment.ts
echo   production: false, >> frontend\contentgruen-frontend\src\environments\environment.ts
echo   baseUrl: '', // Empty for same-origin requests (Docker with nginx proxy) >> frontend\contentgruen-frontend\src\environments\environment.ts
echo   useKeycloak: 'false' >> frontend\contentgruen-frontend\src\environments\environment.ts
echo }; >> frontend\contentgruen-frontend\src\environments\environment.ts

echo Environment reset to Docker mode.
echo You can now run: run-docker.bat
