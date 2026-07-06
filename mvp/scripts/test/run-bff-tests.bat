@echo off
echo =====================================
echo Running .NET BFF Tests
echo =====================================
echo.

cd /d "%~dp0\..\..\backend\BFF"

REM Check if .NET SDK is available
dotnet --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] .NET SDK is not installed or not in PATH
    echo Please install .NET SDK from https://dotnet.microsoft.com/download
    exit /b 1
)

REM Run .NET tests
echo Running .NET tests...
dotnet test --no-restore --verbosity quiet

if %ERRORLEVEL% neq 0 (
    echo.
    echo [FAIL] BFF tests failed!
    exit /b %ERRORLEVEL%
) else (
    echo [OK] BFF tests passed!
)

echo.
echo =====================================
echo BFF tests completed successfully!
echo =====================================
