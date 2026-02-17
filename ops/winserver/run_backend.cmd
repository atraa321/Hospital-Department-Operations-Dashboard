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

if "%BACKEND_PORT%"=="" set "BACKEND_PORT=18080"

set "BACKEND_DIR=%ROOT%\backend"
set "VENV_PY=%BACKEND_DIR%\.venv312\Scripts\python.exe"
set "LOG_DIR=%ROOT%\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

if not exist "%VENV_PY%" (
  echo [ERROR] Python venv not found: %VENV_PY%
  exit /b 1
)

pushd "%BACKEND_DIR%" || exit /b 1
if not exist ".env" copy /Y ".env.example" ".env" >nul

echo [RUN] backend on 0.0.0.0:%BACKEND_PORT%
"%VENV_PY%" -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% 1>>"%LOG_DIR%\backend.stdout.log" 2>>"%LOG_DIR%\backend.stderr.log"
set "EXIT_CODE=%ERRORLEVEL%"
popd

exit /b %EXIT_CODE%
