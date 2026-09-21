# run.ps1
# This script sets up a local development environment (only once) and runs the app directly.

$VenvPath = "$PSScriptRoot\.venv"

# 1. Create the virtual environment if it doesn't exist
if (-not (Test-Path "$VenvPath")) {
    Write-Host "Setting up local development environment for the first time..." -ForegroundColor Cyan
    python -m venv $VenvPath
    
    # 2. Install the required libraries
    Write-Host "Installing required libraries (PyQt6, mutagen, requests)..." -ForegroundColor Cyan
    & "$VenvPath\Scripts\pip.exe" install -r "$PSScriptRoot\requirements.txt"
}

# 3. Run the application
Write-Host "Starting Audio Tagger..." -ForegroundColor Green
& "$VenvPath\Scripts\python.exe" "$PSScriptRoot\app.py"
