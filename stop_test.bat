@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo Stopping CyberCafe services...
echo.

echo Stopping server windows...
taskkill /F /FI "WINDOWTITLE eq CyberCafe Server*" >nul 2>&1

echo Stopping dashboard windows...
taskkill /F /FI "WINDOWTITLE eq CyberCafe Dashboard*" >nul 2>&1

echo Stopping client app...
taskkill /F /IM "CyberCafe Client.exe" >nul 2>&1
taskkill /F /IM pythonw.exe >nul 2>&1

REM Dev-mode client started via python main.py
powershell -NoProfile -Command ^
  "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'client\\main\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

REM Uvicorn on port 8000 if still running outside titled window
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%p >nul 2>&1
)

echo.
echo All services stopped!
pause
