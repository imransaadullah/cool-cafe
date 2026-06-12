@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo ========================================
echo   CyberCafe Setup and Start
echo ========================================
echo.

REM Idempotent setup: deps, admin user, dashboard npm
python setup.py
if errorlevel 1 (
    echo.
    echo Setup failed. Fix the errors above and try again.
    pause
    exit /b 1
)

REM Sync Prisma schema + client before starting server (picks up schema changes)
echo.
echo Syncing Prisma database and client...
python setup.py --prisma-only
if errorlevel 1 (
    echo.
    echo Prisma sync failed. Fix the errors above and try again.
    pause
    exit /b 1
)

echo.
echo Starting services...
echo.

REM Local server (LAN accessible for client PCs)
start "CyberCafe Server" cmd /k "cd /d %~dp0 && python -m uvicorn local_server.app.main:app --reload --host 0.0.0.0 --port 8000"

echo Waiting for server...
set /a retries=0
:wait_server
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8000/api/health' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if %errorlevel% equ 0 goto server_ready
timeout /t 1 /nobreak >nul
set /a retries+=1
if %retries% lss 20 goto wait_server
echo   Warning: server health check timed out - it may still be starting
:server_ready

REM Dashboard
start "CyberCafe Dashboard" cmd /k "cd /d %~dp0dashboard\frontend && npm run dev"
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo   Services Running
echo ========================================
echo.
echo   Server:     http://localhost:8000
echo   Dashboard:  http://localhost:3000
echo   API Docs:   http://localhost:8000/docs
echo   Health:     http://localhost:8000/api/health
echo.
echo   Login: admin / admin123
echo.
echo   Client PCs should use server URL:
echo     http://^<THIS-PC-LAN-IP^>:8000
echo.
echo   Client launch options:
echo     - client\start_client.bat   (recommended, no terminal)
echo     - client\main.pyw           (double-click)
echo     - cd client ^&^& python main.py   (debug, shows terminal)
echo.
echo   Reset client to factory defaults:
echo     - client\reset_client.bat
echo.
set /p launch_client="Start client on this PC now? [Y/n]: "
if /i "%launch_client%"=="n" goto done
if /i "%launch_client%"=="no" goto done

start "" "%~dp0client\start_client.bat"
echo   Client launched.

:done
echo.
echo All services started!
pause
