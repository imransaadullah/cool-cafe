@echo off
REM Launch CyberCafe client without a console window
cd /d "%~dp0"

where pythonw >nul 2>&1
if %errorlevel% neq 0 (
    echo pythonw not found. Install Python and ensure it is on PATH.
    pause
    exit /b 1
)

python "%~dp0..\scripts\service_guard.py" client 2>nul
if %errorlevel% equ 0 (
    echo Client is already running.
    exit /b 0
)

REM main.py also enforces single instance if guard script is unavailable
start "" pythonw main.py
