@echo off
REM Launch CyberCafe client without a console window
cd /d "%~dp0"

where pythonw >nul 2>&1
if %errorlevel% neq 0 (
    echo pythonw not found. Install Python and ensure it is on PATH.
    pause
    exit /b 1
)

start "" pythonw main.py
