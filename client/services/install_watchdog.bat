@echo off
REM CyberCafe Watchdog Service Installer
REM Run this script as Administrator

echo ========================================
echo CyberCafe Watchdog Service Installer
echo ========================================
echo.

REM Check for administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must be run as Administrator!
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Install the service
echo Installing CyberCafe Watchdog Service...
python "%~dp0watchdog_service.py" install

if %errorLevel% equ 0 (
    echo.
    echo Service installed successfully!
    echo.
    echo Starting service...
    python "%~dp0watchdog_service.py" start
    
    if %errorLevel% equ 0 (
        echo.
        echo Service started successfully!
    ) else (
        echo.
        echo WARNING: Service installed but failed to start.
        echo You can start it manually from Services.msc
    )
) else (
    echo.
    echo ERROR: Failed to install service!
)

echo.
echo ========================================
echo Installation Complete
echo ========================================
echo.
echo To manage the service:
echo   - Open Services.msc
echo   - Look for "CyberCafe Client Watchdog"
echo   - Right-click for options
echo.
pause
