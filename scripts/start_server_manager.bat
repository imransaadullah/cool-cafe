@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

python scripts\service_guard.py desktop
if %errorlevel% equ 0 exit /b 0

start "CyberCafe Server Manager" cmd /k "cd /d %~dp0..\local_server && python server_manager.py"
