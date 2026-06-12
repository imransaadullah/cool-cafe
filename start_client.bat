@echo off
REM Launch the CyberCafe client (delegates to client folder)
cd /d "%~dp0client"
call start_client.bat
