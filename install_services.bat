@echo off
REM CyberCafe Service Installer
REM Installs both Client Watchdog and Server as Windows Services

echo.
echo ========================================
echo   CyberCafe Service Installer
echo ========================================
echo.

REM Check for administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script requires administrator privileges.
    echo Please right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check for pywin32
python -c "import win32serviceutil" >nul 2>&1
if errorlevel 1 (
    echo Installing pywin32...
    pip install pywin32
)

echo.
echo Select installation option:
echo   1. Install Client Watchdog Service
echo   2. Install Server Service
echo   3. Install Both Services
echo   4. Uninstall Client Watchdog Service
echo   5. Uninstall Server Service
echo   6. Uninstall Both Services
echo.

set /p choice="Enter choice (1-6): "

if "%choice%"=="1" goto install_client
if "%choice%"=="2" goto install_server
if "%choice%"=="3" goto install_both
if "%choice%"=="4" goto uninstall_client
if "%choice%"=="5" goto uninstall_server
if "%choice%"=="6" goto uninstall_both
echo Invalid choice
pause
exit /b 1

:install_client
echo.
echo Installing Client Watchdog Service...
python "%~dp0client\services\watchdog_service.py" install
python "%~dp0client\services\watchdog_service.py" start
echo Client Watchdog Service installed and started.
goto end

:install_server
echo.
echo Installing Server Service...
python "%~dp0local_server\services\server_service.py" install
python "%~dp0local_server\services\server_service.py" start
echo Server Service installed and started.
goto end

:install_both
echo.
echo Installing Client Watchdog Service...
python "%~dp0client\services\watchdog_service.py" install
python "%~dp0client\services\watchdog_service.py" start
echo.
echo Installing Server Service...
python "%~dp0local_server\services\server_service.py" install
python "%~dp0local_server\services\server_service.py" start
echo Both services installed and started.
goto end

:uninstall_client
echo.
echo Uninstalling Client Watchdog Service...
python "%~dp0client\services\watchdog_service.py" stop
python "%~dp0client\services\watchdog_service.py" remove
echo Client Watchdog Service uninstalled.
goto end

:uninstall_server
echo.
echo Uninstalling Server Service...
python "%~dp0local_server\services\server_service.py" stop
python "%~dp0local_server\services\server_service.py" remove
echo Server Service uninstalled.
goto end

:uninstall_both
echo.
echo Uninstalling Client Watchdog Service...
python "%~dp0client\services\watchdog_service.py" stop
python "%~dp0client\services\watchdog_service.py" remove
echo.
echo Uninstalling Server Service...
python "%~dp0local_server\services\server_service.py" stop
python "%~dp0local_server\services\server_service.py" remove
echo Both services uninstalled.
goto end

:end
echo.
echo Done!
pause
