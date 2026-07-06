# PowerShell wrapper for run-local.bat
# This script simply calls the batch file which handles the actual setup

# Change to the script directory first
Push-Location $PSScriptRoot

try {
    if (Test-Path ".\run-local.bat") {
        Write-Host "Starting ContentGruen via run-local.bat..." -ForegroundColor Green
        # Call the batch file from the current directory
        cmd.exe /c "run-local.bat"
    } else {
        Write-Host "Error: run-local.bat not found in current directory" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
} finally {
    Pop-Location
}
