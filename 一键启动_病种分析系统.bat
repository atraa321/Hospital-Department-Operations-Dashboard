@echo off
setlocal EnableDelayedExpansion

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

if not exist "%ROOT%\scripts\start_backend.cmd" (
  echo [ERROR] Missing file: scripts\start_backend.cmd
  pause
  exit /b 1
)

if not exist "%ROOT%\scripts\start_frontend.cmd" (
  echo [ERROR] Missing file: scripts\start_frontend.cmd
  pause
  exit /b 1
)

echo ==========================================
echo Disease Analytics System - One Click Start
echo ROOT: %ROOT%
echo ==========================================

start "DiseaseAnalytics-Backend" cmd /k ""%ROOT%\scripts\start_backend.cmd""
echo [INFO] Waiting backend health...
set "BACKEND_HEALTH=FAIL"
for /l %%I in (1,1,20) do (
  for /f "delims=" %%R in ('powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:18080/api/v1/health -TimeoutSec 2; if($r.StatusCode -eq 200){'OK'} else {'FAIL'} } catch {'FAIL'}"') do set "BACKEND_HEALTH=%%R"
  if /i "!BACKEND_HEALTH!"=="OK" goto backend_ready
  ping 127.0.0.1 -n 2 >nul
)

echo [WARN] Backend health check timeout. Frontend will still start.
:backend_ready
start "DiseaseAnalytics-Frontend" cmd /k ""%ROOT%\scripts\start_frontend.cmd""

echo [INFO] Waiting services to boot...
ping 127.0.0.1 -n 4 >nul

set "BACKEND_PORT=DOWN"
set "FRONTEND_STATUS=DOWN"
set "FRONTEND_LISTEN_PORT="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":18080 .*LISTENING"') do set "BACKEND_PORT=UP"
for %%F in (5173 4173 5202 3000 8080) do (
  for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%%F .*LISTENING"') do (
    set "FRONTEND_STATUS=UP"
    set "FRONTEND_LISTEN_PORT=%%F"
  )
  if /i "!FRONTEND_STATUS!"=="UP" goto frontend_port_ready
)

:frontend_port_ready

echo [CHECK] Backend port 18080: %BACKEND_PORT%
if "%FRONTEND_STATUS%"=="UP" (
  echo [CHECK] Frontend port %FRONTEND_LISTEN_PORT%: UP
) else (
  echo [CHECK] Frontend port: DOWN
)

set "BACKEND_HEALTH=FAIL"
for /f "delims=" %%R in ('powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:18080/api/v1/health -TimeoutSec 2; if($r.StatusCode -eq 200){'OK'} else {'FAIL'} } catch {'FAIL'}"') do set "BACKEND_HEALTH=%%R"
echo [CHECK] Backend health API: %BACKEND_HEALTH%

echo.
echo Access URLs:
echo - Backend : http://127.0.0.1:18080/api/v1/health
if "%FRONTEND_STATUS%"=="UP" (
  echo - Frontend: http://127.0.0.1:%FRONTEND_LISTEN_PORT%
) else (
  echo - Frontend: http://127.0.0.1:5173
)
echo.
if "%FRONTEND_STATUS%"=="DOWN" (
  echo [WARN] Frontend is not listening on known ports.
  echo        Please check the "DiseaseAnalytics-Frontend" window for exact error.
)
if "%BACKEND_PORT%"=="DOWN" (
  echo [WARN] Backend is not listening on 18080.
  echo        Please check the "DiseaseAnalytics-Backend" window for exact error.
)
echo.
pause
