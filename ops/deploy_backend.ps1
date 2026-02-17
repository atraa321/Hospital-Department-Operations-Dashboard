param(
  [string]$ProjectRoot = "D:\病种分析V2",
  [string]$PythonExe = "py -3.12",
  [int]$Port = 18080
)

$ErrorActionPreference = "Stop"

$backendPath = Join-Path $ProjectRoot "backend"
Set-Location $backendPath

if (-not (Test-Path ".venv312")) {
  & $PythonExe -m venv .venv312
}

& ".\.venv312\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv312\Scripts\pip.exe" install -r requirements.txt

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}

Write-Host "Backend dependencies are ready."
Write-Host "Run service command:"
Write-Host ".\.venv312\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port $Port"
