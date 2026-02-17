@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%ops\winserver\manual_oneclick_deploy.ps1"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [ERROR] Deployment failed, exit code: %EXIT_CODE%
  pause
)

exit /b %EXIT_CODE%
