@echo off
REM CyberCafe Build Script for Windows

echo.
echo ========================================
echo   CyberCafe Build Script
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Run the Python build script
python build.py

pause
