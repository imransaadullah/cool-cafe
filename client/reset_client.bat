@echo off
REM Reset CyberCafe client — run as Administrator for full system cleanup
cd /d "%~dp0"

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting Administrator privileges for full system cleanup...
    powershell -NoProfile -Command "Start-Process -FilePath 'python' -ArgumentList '\"%~dp0reset_client.py\" %*' -Verb RunAs -Wait"
    exit /b %errorLevel%
)

python reset_client.py %*
