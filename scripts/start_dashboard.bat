@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

python scripts\service_guard.py dashboard
if %errorlevel% equ 0 exit /b 0

start "CyberCafe Dashboard" cmd /k "cd /d %~dp0..\dashboard\frontend && npm run dev"
