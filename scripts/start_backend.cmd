@echo off
setlocal

set "ROOT=%~dp0.."
set "VENV_DIR=.venv312"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
pushd "%ROOT%\backend" || (
  echo [ERROR] backend path not found.
  pause
  exit /b 1
)

set "NEED_VENV_CREATE=0"
if not exist "%VENV_PY%" set "NEED_VENV_CREATE=1"

if "%NEED_VENV_CREATE%"=="0" (
  "%VENV_PY%" -c "import sys" >nul 2>nul
  if errorlevel 1 (
    echo [INIT] Existing venv python is invalid, recreating %VENV_DIR%
    set "NEED_VENV_CREATE=1"
  ) else (
    "%VENV_PY%" -m pip --version >nul 2>nul
    if errorlevel 1 (
      echo [INIT] Existing venv missing pip, recreating %VENV_DIR%
      set "NEED_VENV_CREATE=1"
    )
  )
)

if "%NEED_VENV_CREATE%"=="1" (
  if exist "%VENV_DIR%" (
    echo [INIT] Stop running processes using %VENV_DIR%
    call :stop_venv_processes
    call :cleanup_venv
  )

  if exist "%VENV_DIR%" (
    echo [ERROR] Cannot remove %VENV_DIR%. It may still be in use.
    echo         Close backend windows and retry.
    pause
    popd
    exit /b 1
  )

  echo [INIT] Create Python venv .venv312
  call :create_venv
  if errorlevel 1 (
    echo [ERROR] Python virtual env create failed.
    pause
    popd
    exit /b 1
  )

  "%VENV_PY%" -m ensurepip --upgrade >nul 2>nul
  "%VENV_PY%" -m pip --version >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] pip is unavailable in %VENV_DIR%.
    pause
    popd
    exit /b 1
  )
)

if not exist "%VENV_PY%" (
  echo [ERROR] Python virtual env create failed.
  pause
  popd
  exit /b 1
)

echo [INIT] Ensure backend dependencies
"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] Backend dependencies install failed.
  pause
  popd
  exit /b 1
)

if not exist ".env" copy /Y .env.example .env >nul

echo [RUN] Backend on 0.0.0.0:18080
"%VENV_PY%" -m uvicorn app.main:app --host 0.0.0.0 --port 18080 --reload

echo [EXIT] Backend process stopped.
popd
pause
exit /b 0

:cleanup_venv
setlocal EnableDelayedExpansion
set /a RETRY=0
:cleanup_retry
if not exist "%VENV_DIR%" (
  endlocal
  exit /b 0
)
attrib -r /s /d "%VENV_DIR%\*" >nul 2>nul
rmdir /s /q "%VENV_DIR%" >nul 2>nul
if not exist "%VENV_DIR%" (
  endlocal
  exit /b 0
)
powershell -NoProfile -Command "try { Remove-Item -LiteralPath '.\%VENV_DIR%' -Recurse -Force -ErrorAction Stop } catch {}" >nul 2>nul
if not exist "%VENV_DIR%" (
  endlocal
  exit /b 0
)
set /a RETRY+=1
if !RETRY! GEQ 10 (
  endlocal
  exit /b 1
)
ping 127.0.0.1 -n 2 >nul
goto cleanup_retry

:create_venv
where py >nul 2>nul
if %errorlevel%==0 (
  py -3.12 -m venv "%VENV_DIR%"
  if not errorlevel 1 exit /b 0
)
python -m venv "%VENV_DIR%"
if errorlevel 1 exit /b 1
exit /b 0

:stop_venv_processes
for /f %%P in ('powershell -NoProfile -Command "$venv=(Resolve-Path '.\%VENV_DIR%').Path; $ids=New-Object 'System.Collections.Generic.HashSet[int]'; $procs=Get-CimInstance Win32_Process; foreach($p in $procs){ if($p.ExecutablePath -and $p.ExecutablePath.StartsWith($venv, [System.StringComparison]::OrdinalIgnoreCase)){ [void]$ids.Add([int]$p.ProcessId) } }; $py=Get-Process -Name python -ErrorAction SilentlyContinue; foreach($proc in $py){ try { foreach($m in $proc.Modules){ if($m.FileName -and $m.FileName.StartsWith($venv, [System.StringComparison]::OrdinalIgnoreCase)){ [void]$ids.Add([int]$proc.Id); break } } } catch {} }; foreach($id in $ids){ $id }"') do (
  taskkill /PID %%P /F >nul 2>nul
)
exit /b 0
