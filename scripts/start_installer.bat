@echo off
cd /d "%~dp0.."
python -m pip install -r installer\requirements.txt -q
python -m installer.main
