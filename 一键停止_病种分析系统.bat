@echo off
setlocal EnableExtensions EnableDelayedExpansion

echo ==========================================
echo Disease Analytics System - One Click Stop
echo ==========================================

call :kill_by_title "DiseaseAnalytics-Backend"
call :kill_by_title "DiseaseAnalytics-Frontend"

call :kill_by_port 18080
for %%F in (5173 4173 5202 3000 8080) do call :kill_by_port %%F

echo.
echo Stop operation completed.
pause
exit /b 0

:kill_by_title
set "TITLE=%~1"
set "FOUND=0"
for /f "tokens=2 delims=," %%P in ('tasklist /v /fo csv ^| findstr /i /c:%TITLE%') do (
  set "PID=%%~P"
  if not "!PID!"=="" (
    taskkill /PID !PID! /T /F >nul 2>nul
    if !errorlevel! equ 0 (
      set "FOUND=1"
      echo [OK] Closed window: %TITLE% (PID !PID!)
    )
  )
)
if "!FOUND!"=="0" (
  echo [INFO] Window not found: %TITLE%
)
exit /b 0

:kill_by_port
set "PORT=%~1"
set "FOUND=0"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
  set "PID=%%P"
  if not "!PID!"=="0" (
    taskkill /PID !PID! /T /F >nul 2>nul
    if !errorlevel! equ 0 (
      set "FOUND=1"
      echo [OK] Released port: %PORT% (PID !PID!)
    )
  )
)
if "!FOUND!"=="0" (
  echo [INFO] Port %PORT% is not listening
)
exit /b 0
