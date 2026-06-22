@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

echo.
echo ============================================================
echo   CyberCafe Unified Installer Build
echo   Builds Local Server + Global Server + Client, then packages
echo ============================================================
echo.

set ERR=0

:: --- Dashboard (for local server bundle) ---
where npm >nul 2>&1
if %errorlevel% equ 0 (
  echo [1/5] Building dashboard...
  pushd dashboard\frontend
  call npm install
  if %errorlevel% neq 0 set ERR=1
  call npm run build
  if %errorlevel% neq 0 set ERR=1
  popd
) else (
  echo WARNING: npm not found - local server will ship without embedded dashboard.
)
if %ERR% neq 0 goto :fail

:: --- Python build deps ---
echo.
echo [2/5] Installing PyInstaller build dependencies...
python -m pip install -r client\requirements-build.txt
python -m pip install -r local_server\requirements-build.txt
python -m pip install -r global_server\requirements-build.txt
python -m pip install -r installer\requirements.txt
python -m pip install prisma
if %errorlevel% neq 0 goto :fail

python scripts\prisma_generate.py
if %errorlevel% neq 0 goto :fail

:: --- PyInstaller: all three roles ---
echo.
echo [3/5] Building Local Server...
cd local_server
python -m PyInstaller build.spec --noconfirm
if %errorlevel% neq 0 goto :fail
cd ..

echo.
echo [3/5] Building Global Server...
cd global_server
python -m PyInstaller build.spec --noconfirm
if %errorlevel% neq 0 goto :fail
cd ..

echo.
echo [3/5] Building Client...
cd client
python -m PyInstaller build.spec --noconfirm
if %errorlevel% neq 0 goto :fail
cd ..

:: --- Stage payload for Inno Setup ---
echo.
echo [4/5] Staging installer payload...
if exist deploy\installer\payload rmdir /S /Q deploy\installer\payload
mkdir deploy\installer\payload
mkdir deploy\installer\payload\local_server
mkdir deploy\installer\payload\global_server
mkdir deploy\installer\payload\client

xcopy /E /I /Y "local_server\dist\CyberCafe Server\*" "deploy\installer\payload\local_server\" >nul
xcopy /E /I /Y "global_server\dist\CyberCafe Global Server\*" "deploy\installer\payload\global_server\" >nul
xcopy /E /I /Y "client\dist\CyberCafe Client\*" "deploy\installer\payload\client\" >nul

:: --- Graphical installer (PyQt) ---
echo.
echo [5/5] Building unified graphical installer...
cd installer
python -m PyInstaller build.spec --noconfirm
if %errorlevel% neq 0 goto :fail
cd ..

if not exist deploy\installer\installer_output mkdir deploy\installer\installer_output
copy /Y "installer\dist\CyberCafe Setup.exe" "deploy\installer\installer_output\CyberCafe Setup.exe" >nul

echo.
echo ============================================================
echo   SUCCESS
echo   Graphical installer: deploy\installer\installer_output\CyberCafe Setup.exe
echo   Portable builds:
echo     local_server\dist\CyberCafe Server\
echo     global_server\dist\CyberCafe Global Server\
echo     client\dist\CyberCafe Client\
echo ============================================================
goto :done

:fail
echo.
echo BUILD FAILED
exit /b 1

:done
echo.
pause
