@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

echo.
echo ========================================
echo   CyberCafe Server Installer Build
echo ========================================
echo.

where npm >nul 2>&1
if %errorlevel% equ 0 (
  echo Building dashboard frontend...
  pushd dashboard\frontend
  call npm install
  if %errorlevel% neq 0 exit /b 1
  call npm run build
  if %errorlevel% neq 0 exit /b 1
  popd
) else (
  echo WARNING: npm not found - dashboard will not be bundled in the installer.
  echo Install Node.js and re-run this script for a full package.
)

echo.
echo Installing Python build dependencies...
python -m pip install -r local_server\requirements-build.txt
python -m pip install prisma
if %errorlevel% neq 0 exit /b 1

python scripts\prisma_generate.py
if %errorlevel% neq 0 exit /b 1

echo.
echo Running PyInstaller...
cd local_server
python -m PyInstaller build.spec --noconfirm
if %errorlevel% neq 0 exit /b 1
cd ..

where iscc >nul 2>&1
if %errorlevel% equ 0 (
  echo.
  echo Creating Inno Setup installer...
  iscc deploy\installer\server_setup.iss
  if %errorlevel% neq 0 exit /b 1
  echo.
  echo Installer: deploy\installer\installer_output\cybercafe_server_setup.exe
) else (
  echo.
  echo Inno Setup not found - portable build only.
  echo Output: local_server\dist\CyberCafe Server\
)

echo.
echo Done.
pause
