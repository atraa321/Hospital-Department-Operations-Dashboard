param(
  [string]$ProjectRoot = "D:\病种分析V2",
  [string]$OutputDir = "D:\deploy\offline-bundles",
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
$frontendEnvProd = Join-Path $frontendPath ".env.production.local"

Ensure-PathExists -Path $backendPath -Label "backend directory"
Ensure-PathExists -Path $frontendPath -Label "frontend directory"
Ensure-PathExists -Path $requirementsPath -Label "backend requirements.txt"

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$bundleRoot = Join-Path $OutputDir "disease_analytics_bundle_$ts"
$wheelDir = Join-Path $bundleRoot "python_wheels"
$distDir = Join-Path $bundleRoot "frontend_dist"
$zipPath = "$bundleRoot.zip"

if (-not (Test-Path $OutputDir)) {
  New-Item -Path $OutputDir -ItemType Directory | Out-Null
}
New-Item -Path $bundleRoot -ItemType Directory | Out-Null
New-Item -Path $wheelDir -ItemType Directory | Out-Null

Write-Host "[1/4] Download backend wheels"
Invoke-Python -Args @("-m", "pip", "download", "-r", $requirementsPath, "-d", $wheelDir)

Write-Host "[2/4] Build frontend dist"
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

Copy-Item (Join-Path $frontendPath "dist") $distDir -Recurse -Force

Write-Host "[3/4] Copy deploy scripts"
Copy-Item (Join-Path $ProjectRoot "ops\winserver") (Join-Path $bundleRoot "ops_winserver") -Recurse -Force
Copy-Item $requirementsPath (Join-Path $bundleRoot "requirements.txt") -Force

@(
  "bundle_created_at=$ts"
  "api_base_url=$ApiBaseUrl"
  "python_version=$PythonVersion"
  "project_root_source=$ProjectRoot"
) | Set-Content -Path (Join-Path $bundleRoot "bundle_manifest.txt") -Encoding UTF8

Write-Host "[4/4] Create zip package"
if (Test-Path $zipPath) {
  Remove-Item $zipPath -Force
}
Compress-Archive -Path (Join-Path $bundleRoot "*") -DestinationPath $zipPath -CompressionLevel Optimal

Write-Host "Offline bundle ready:"
Write-Host "- Folder: $bundleRoot"
Write-Host "- Zip   : $zipPath"
