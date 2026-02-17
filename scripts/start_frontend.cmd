@echo off
setlocal EnableDelayedExpansion

set "ROOT=%~dp0.."
pushd "%ROOT%\frontend" || (
  echo [ERROR] frontend path not found.
  pause
  exit /b 1
)

where npm >nul 2>nul
if not %errorlevel%==0 (
  echo [ERROR] npm not found in PATH.
  pause
  popd
  exit /b 1
)

if not exist "node_modules" (
  echo [INIT] Install frontend dependencies
  npm install
)

if not exist ".env" copy /Y .env.example .env >nul

set "FRONTEND_PORT="
for %%P in (5173 5202 4173 3000 8080) do (
  powershell -NoProfile -Command "$p=%%P; try { $l=[System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Any,$p); $l.Start(); $l.Stop(); exit 0 } catch { exit 1 }" >nul 2>nul
  if !errorlevel! EQU 0 (
    set "FRONTEND_PORT=%%P"
    goto :port_selected
  )
)

:port_selected
if "%FRONTEND_PORT%"=="" (
  echo [ERROR] No available frontend port found from: 5173 5202 4173 3000 8080
  popd
  pause
  exit /b 1
)

echo [RUN] Frontend dev server on %FRONTEND_PORT%
npm run dev -- --host 0.0.0.0 --port %FRONTEND_PORT%

echo [EXIT] Frontend process stopped.
popd
pause
