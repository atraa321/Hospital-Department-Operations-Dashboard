param(
  [string]$ProjectRoot = "D:\病种分析V2",
  [string]$PythonCommand = "py",
  [string]$PythonVersion = "3.12",
  [string]$ApiBaseUrl = "http://127.0.0.1:18080/api/v1"
)

$ErrorActionPreference = "Stop"

function Ensure-PathExists {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][string]$Label
  )
  if (-not (Test-Path $Path)) {
    throw "$Label not found: $Path"
  }
}

function Invoke-Python {
  param(
    [Parameter(Mandatory = $true)][string[]]$Args
  )

  if ($PythonCommand -ieq "py") {
    & py "-$PythonVersion" @Args
  }
  else {
    & $PythonCommand @Args
  }
}

Ensure-PathExists -Path $ProjectRoot -Label "ProjectRoot"
$backendPath = Join-Path $ProjectRoot "backend"
$frontendPath = Join-Path $ProjectRoot "frontend"
$requirementsPath = Join-Path $backendPath "requirements.txt"
$wheelDir = Join-Path $ProjectRoot "ops\winserver\python_wheels"
$frontendEnvProd = Join-Path $frontendPath ".env.production.local"

Ensure-PathExists -Path $backendPath -Label "backend directory"
Ensure-PathExists -Path $frontendPath -Label "frontend directory"
Ensure-PathExists -Path $requirementsPath -Label "backend requirements.txt"

if (Test-Path $wheelDir) {
  Remove-Item -Path $wheelDir -Recurse -Force
}
New-Item -Path $wheelDir -ItemType Directory | Out-Null

Write-Host "[1/2] Download backend wheels to $wheelDir"
Invoke-Python -Args @("-m", "pip", "download", "-r", $requirementsPath, "-d", $wheelDir)

Write-Host "[2/2] Build frontend dist"
Push-Location $frontendPath
try {
  if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm not found. Install Node.js first."
  }
  @(
    "VITE_API_BASE_URL=$ApiBaseUrl"
    "VITE_USER_ID=prod_user"
    "VITE_USER_ROLE=ADMIN"
    "VITE_USER_DEPT="
  ) | Set-Content -Path $frontendEnvProd -Encoding UTF8
  if (Test-Path (Join-Path $frontendPath "package-lock.json")) {
    npm ci
  }
  else {
    npm install
  }
  npm run build
}
finally {
  Pop-Location
}

Write-Host "Offline manual deployment assets are ready:"
Write-Host "- wheelhouse: $wheelDir"
Write-Host "- frontend  : $(Join-Path $frontendPath 'dist')"
