@echo off
setlocal
cd /d "%~dp0"

powershell -ExecutionPolicy Bypass -File "%~dp0start_local.ps1"
if errorlevel 1 (
  echo.
  echo The local server stopped with an error.
  pause
  exit /b 1
)

pause
