@echo off
REM Stop All CyberCafe Services

echo.
echo Stopping CyberCafe Services...
echo.

REM Kill Python processes (uvicorn)
echo Stopping servers...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq CyberCafe Server*" >nul 2>&1
taskkill /F /IM uvicorn.exe >nul 2>&1

REM Kill Node processes (dashboard)
echo Stopping dashboard...
taskkill /F /IM node.exe /FI "WINDOWTITLE eq CyberCafe Dashboard*" >nul 2>&1

REM Kill client
echo Stopping client...
taskkill /F /IM "CyberCafe Client.exe" >nul 2>&1
taskkill /F /IM python.exe /FI "WINDOWTITLE eq CyberCafe Client*" >nul 2>&1

echo.
echo All services stopped!
pause
