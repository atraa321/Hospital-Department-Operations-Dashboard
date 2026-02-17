@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%oneclick_install.ps1"
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo [ERROR] Deployment failed, exit code: %EXIT_CODE%
  pause
)
exit /b %EXIT_CODE%
