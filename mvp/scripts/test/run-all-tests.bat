@echo off
echo =====================================
echo Running All ContentGruen Tests
echo =====================================
echo.

set TESTS_FAILED=0

REM Run Python backend tests
echo [1/3] Running Python Backend Tests...
echo -------------------------------------
call "%~dp0\run-backend-tests.bat"
if %ERRORLEVEL% neq 0 (
    set TESTS_FAILED=1
    echo [FAIL] Python tests failed!
) else (
    echo [OK] Python tests passed!
)
echo.

REM Run Angular frontend tests
echo [2/3] Running Angular Frontend Tests...
echo -------------------------------------
call "%~dp0\run-frontend-tests.bat"
if %ERRORLEVEL% neq 0 (
    set TESTS_FAILED=1
    echo [FAIL] Angular tests failed!
) else (
    echo [OK] Angular tests passed!
)
echo.

REM Run .NET BFF tests
echo [3/3] Running .NET BFF Tests...
echo -------------------------------------
call "%~dp0\run-bff-tests.bat"
if %ERRORLEVEL% neq 0 (
    set TESTS_FAILED=1
    echo [FAIL] BFF tests failed!
) else (
    echo [OK] BFF tests passed!
)
echo.

REM Summary
echo =====================================
if %TESTS_FAILED% equ 0 (
    echo SUCCESS: All tests passed!
    exit /b 0
) else (
    echo FAILURE: Some tests failed!
    exit /b 1
)
echo =====================================
