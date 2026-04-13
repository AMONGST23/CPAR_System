@echo off
setlocal
cd /d "%~dp0"

powershell -ExecutionPolicy Bypass -File "%~dp0backup_db.ps1"
if errorlevel 1 (
  echo.
  echo Backup failed.
  pause
  exit /b 1
)

pause
