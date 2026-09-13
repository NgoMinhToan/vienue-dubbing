@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" (
  echo Please run Setup.ps1 first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\start.py
pause
