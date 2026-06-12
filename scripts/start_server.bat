@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

python scripts\service_guard.py server
if %errorlevel% equ 0 exit /b 0

start "CyberCafe Server" cmd /k "cd /d %~dp0.. && python -m uvicorn local_server.app.main:app --reload --reload-dir local_server --reload-dir shared --host 0.0.0.0 --port 8000"
