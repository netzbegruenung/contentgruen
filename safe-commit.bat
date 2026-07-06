@echo off
REM Safe commit script that handles pre-commit hooks

if "%~1"=="" (
    echo Usage: safe-commit.bat "commit message"
    exit /b 1
)

echo Attempting commit...
git commit -m "%~1"
if %errorlevel% equ 0 (
    echo Commit successful on first try
    exit /b 0
)

echo Pre-commit hook made changes. Reviewing...
echo ----------------------------------------
echo Files modified by pre-commit hook:
git diff --name-only --cached
echo ----------------------------------------

REM Auto-stage formatting changes
git add -u

echo Re-attempting commit with formatted files...
git commit -m "%~1"
if %errorlevel% equ 0 (
    echo Commit successful after formatting
) else (
    echo Commit still failed. Manual intervention needed.
    echo Run: git status
    exit /b 1
)
