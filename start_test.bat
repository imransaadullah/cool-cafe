@echo off
REM CyberCafe - Setup and Start

echo.
echo ========================================
echo   CyberCafe Setup and Start
echo ========================================
echo.

REM Run setup (idempotent - safe to run multiple times)
python setup.py

echo.
echo Starting services...
echo.

REM Start Local Server
start "CyberCafe Server" cmd /k "cd /d %~dp0 && python -m uvicorn local_server.app.main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 3 /nobreak >nul

REM Start Dashboard
start "CyberCafe Dashboard" cmd /k "cd /d %~dp0dashboard\frontend && npm run dev"
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo   Services Running
echo ========================================
echo.
echo   Server:    http://localhost:8000
echo   Dashboard: http://localhost:3000
echo   API Docs:  http://localhost:8000/docs
echo.
echo   Login: admin / admin123
echo.
echo   Press any key to start client...
pause >nul

start "" "%~dp0client\start_client.bat"

echo.
echo All services started!
pause
