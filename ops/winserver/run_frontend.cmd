@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "ROOT=%SCRIPT_DIR%..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

set "ENV_FILE=%SCRIPT_DIR%service.env"
if not exist "%ENV_FILE%" (
  copy /Y "%SCRIPT_DIR%service.env.example" "%ENV_FILE%" >nul
)
for /f "usebackq tokens=1,2 delims==" %%A in ("%ENV_FILE%") do (
  if not "%%~A"=="" set "%%~A=%%~B"
)

if "%FRONTEND_PORT%"=="" set "FRONTEND_PORT=5173"

set "VENV_PY=%ROOT%\backend\.venv312\Scripts\python.exe"
set "SERVE_SCRIPT=%SCRIPT_DIR%serve_frontend.py"
set "DIST_DIR=%ROOT%\frontend\dist"
set "LOG_DIR=%ROOT%\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

if not exist "%VENV_PY%" (
  echo [ERROR] Python venv not found: %VENV_PY%
  exit /b 1
)
if not exist "%SERVE_SCRIPT%" (
  echo [ERROR] script not found: %SERVE_SCRIPT%
  exit /b 1
)
if not exist "%DIST_DIR%\index.html" (
  echo [ERROR] frontend dist not found: %DIST_DIR%
  exit /b 1
)

echo [RUN] frontend static on 0.0.0.0:%FRONTEND_PORT%
"%VENV_PY%" "%SERVE_SCRIPT%" --dist "%DIST_DIR%" --host 0.0.0.0 --port %FRONTEND_PORT% 1>>"%LOG_DIR%\frontend.stdout.log" 2>>"%LOG_DIR%\frontend.stderr.log"
set "EXIT_CODE=%ERRORLEVEL%"

exit /b %EXIT_CODE%
