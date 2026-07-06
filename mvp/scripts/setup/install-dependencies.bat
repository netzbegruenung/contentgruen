@echo off
echo =====================================
echo Installing ContentGruen Dependencies
echo =====================================
echo.

cd /d "%~dp0\..\.."

REM Install Python dependencies
echo [1/3] Installing Python dependencies...
echo -------------------------------------
cd backend\semantic-search-service
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)
echo Installing Python packages...
venv\Scripts\pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install Python dependencies
    exit /b 1
)
echo [OK] Python dependencies installed
cd ..\..
echo.

REM Install .NET dependencies
echo [2/3] Installing .NET dependencies...
echo -------------------------------------
cd backend\BFF
dotnet restore
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install .NET dependencies
    exit /b 1
)
echo [OK] .NET dependencies installed
cd ..\..
echo.

REM Install Node.js dependencies
echo [3/3] Installing Node.js dependencies...
echo -------------------------------------
cd frontend\contentgruen-frontend
npm install
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install Node.js dependencies
    exit /b 1
)
echo [OK] Node.js dependencies installed
cd ..\..
echo.

echo =====================================
echo All dependencies installed successfully!
echo =====================================
