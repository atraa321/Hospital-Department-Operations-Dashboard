param(
  [string]$ProjectRoot = "D:\病种分析V2",
  [string]$PythonCommand = "py",
  [string]$PythonVersion = "3.12",
  [string]$WheelhouseDir = "",
  [string]$DatabaseUrl = "",
  [int]$BackendPort = 18080,
  [int]$FrontendPort = 5173,
  [string]$ApiBaseUrl = "",
  [string]$CorsOriginsJson = "",
  [string]$PrebuiltFrontendDist = "",
  [bool]$InitDatabase = $true,
  [bool]$SeedData = $false,
  [string]$SeedDataDir = "",
  [bool]$InstallServices = $true,
  [bool]$OpenFirewall = $true
)

$ErrorActionPreference = "Stop"

function Set-EnvValue {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][string]$Key,
    [Parameter(Mandatory = $true)][string]$Value
  )

  $lines = @()
  if (Test-Path $Path) {
    $lines = Get-Content $Path
  }
  $updated = $false
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match "^\s*$Key=") {
      $lines[$i] = "$Key=$Value"
      $updated = $true
      break
    }
  }
  if (-not $updated) {
    $lines += "$Key=$Value"
  }
  Set-Content -Path $Path -Value $lines -Encoding UTF8
}

function Get-EnvValue {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][string]$Key
  )

  if (-not (Test-Path $Path)) {
    return ""
  }

  $line = Get-Content $Path | Where-Object { $_ -match "^\s*$Key=" } | Select-Object -First 1
  if (-not $line) {
    return ""
  }
  return $line.Substring($line.IndexOf("=") + 1).Trim()
}

function Ensure-FirewallRule {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][int]$Port
  )

  $rule = Get-NetFirewallRule -DisplayName $Name -ErrorAction SilentlyContinue
  if ($rule) {
    Write-Host "[INFO] firewall rule exists: $Name"
    return
  }
  New-NetFirewallRule -DisplayName $Name -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port | Out-Null
  Write-Host "[OK] firewall rule added: $Name (TCP/$Port)"
}

function Invoke-PythonCreateVenv {
  param(
    [Parameter(Mandatory = $true)][string]$BackendPath,
    [Parameter(Mandatory = $true)][string]$PythonCommand,
    [Parameter(Mandatory = $true)][string]$PythonVersion
  )

  Push-Location $BackendPath
  try {
    if ($PythonCommand -ieq "py") {
      & py "-$PythonVersion" -m venv .venv312
    }
    else {
      & $PythonCommand -m venv .venv312
    }
  }
  finally {
    Pop-Location
  }
}

function Ensure-DatabaseExists {
  param(
    [Parameter(Mandatory = $true)][string]$PythonExe,
    [Parameter(Mandatory = $true)][string]$BackendPath,
    [Parameter(Mandatory = $true)][string]$DbUrl
  )

  $scriptPath = Join-Path $BackendPath "scripts\init_database.py"
  Ensure-PathExists -Path $scriptPath -Label "database init script"
  & $PythonExe $scriptPath --database-url $DbUrl
  if ($LASTEXITCODE -ne 0) {
    throw "init_database.py failed with exit code $LASTEXITCODE"
  }
}

function Normalize-DatabaseUrl {
  param(
    [Parameter(Mandatory = $true)][string]$PythonExe,
    [Parameter(Mandatory = $true)][string]$BackendPath,
    [Parameter(Mandatory = $true)][string]$DbUrl
  )

  $scriptPath = Join-Path $BackendPath "scripts\normalize_database_url.py"
  Ensure-PathExists -Path $scriptPath -Label "database url normalize script"
  $output = & $PythonExe $scriptPath --database-url $DbUrl
  if ($LASTEXITCODE -ne 0) {
    throw "normalize_database_url.py failed with exit code $LASTEXITCODE"
  }
  if (-not $output) {
    return $DbUrl
  }
  return ($output | Select-Object -Last 1).Trim()
}

function Import-SeedData {
  param(
    [Parameter(Mandatory = $true)][string]$PythonExe,
    [Parameter(Mandatory = $true)][string]$BackendPath,
    [Parameter(Mandatory = $true)][string]$SeedDir
  )

  $scriptPath = Join-Path $BackendPath "scripts\seed_data_init.py"
  Ensure-PathExists -Path $scriptPath -Label "seed data init script"
  Ensure-PathExists -Path $SeedDir -Label "SeedDataDir"
  & $PythonExe $scriptPath --seed-dir $SeedDir
  if ($LASTEXITCODE -ne 0) {
    throw "seed_data_init.py failed with exit code $LASTEXITCODE"
  }
}

function Repair-InstallServicesScript {
  param(
    [Parameter(Mandatory = $true)][string]$OpsWinPath
  )

  $path = Join-Path $OpsWinPath "install_services.ps1"
  if (-not (Test-Path $path)) {
    return
  }

  $text = Get-Content -Path $path -Raw
  $normalized = $text `
    -replace [char]0x201C, '"' `
    -replace [char]0x201D, '"' `
    -replace [char]0x2018, "'" `
    -replace [char]0x2019, "'"
  if ($normalized -ne $text) {
    Set-Content -Path $path -Value $normalized -Encoding UTF8
  }
}

function Ensure-PathExists {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][string]$Label
  )
  if (-not (Test-Path $Path)) {
    throw "$Label not found: $Path"
  }
}

Ensure-PathExists -Path $ProjectRoot -Label "ProjectRoot"

$backendPath = Join-Path $ProjectRoot "backend"
$frontendPath = Join-Path $ProjectRoot "frontend"
$opsWinPath = Join-Path $ProjectRoot "ops\winserver"
$venvPython = Join-Path $backendPath ".venv312\Scripts\python.exe"
$backendEnv = Join-Path $backendPath ".env"
$backendEnvExample = Join-Path $backendPath ".env.example"
$frontendEnvProd = Join-Path $frontendPath ".env.production.local"
$frontendDist = Join-Path $frontendPath "dist"
$serviceEnv = Join-Path $opsWinPath "service.env"
$serviceEnvExample = Join-Path $opsWinPath "service.env.example"

Ensure-PathExists -Path $backendPath -Label "backend directory"
Ensure-PathExists -Path $frontendPath -Label "frontend directory"
Ensure-PathExists -Path $opsWinPath -Label "ops\\winserver directory"
Ensure-PathExists -Path $backendEnvExample -Label "backend .env.example"
Ensure-PathExists -Path $serviceEnvExample -Label "service.env.example"

if (-not (Test-Path $venvPython)) {
  Write-Host "[INIT] create backend virtual environment"
  Invoke-PythonCreateVenv -BackendPath $backendPath -PythonCommand $PythonCommand -PythonVersion $PythonVersion
}

Write-Host "[INIT] install backend dependencies"
if ($WheelhouseDir) {
  Ensure-PathExists -Path $WheelhouseDir -Label "WheelhouseDir"
  & $venvPython -m pip install --no-index --find-links "$WheelhouseDir" -r (Join-Path $backendPath "requirements.txt")
}
else {
  & $venvPython -m pip install --upgrade pip
  & $venvPython -m pip install -r (Join-Path $backendPath "requirements.txt")
}

if (-not (Test-Path $backendEnv)) {
  Copy-Item $backendEnvExample $backendEnv -Force
}

Set-EnvValue -Path $backendEnv -Key "APP_ENV" -Value "prod"
Set-EnvValue -Path $backendEnv -Key "DEBUG" -Value "false"
Set-EnvValue -Path $backendEnv -Key "APP_PORT" -Value "$BackendPort"

$resolvedDbUrl = ""
if ($DatabaseUrl) {
  $resolvedDbUrl = Normalize-DatabaseUrl -PythonExe $venvPython -BackendPath $backendPath -DbUrl $DatabaseUrl
  Set-EnvValue -Path $backendEnv -Key "DATABASE_URL" -Value $resolvedDbUrl
}
else {
  $resolvedDbUrl = Get-EnvValue -Path $backendEnv -Key "DATABASE_URL"
  if (-not $resolvedDbUrl) {
    throw "DATABASE_URL is missing in backend\\.env. Please pass -DatabaseUrl."
  }
  if ($resolvedDbUrl -match "root:password@") {
    throw "DATABASE_URL still uses template password. Please pass -DatabaseUrl."
  }
  $resolvedDbUrl = Normalize-DatabaseUrl -PythonExe $venvPython -BackendPath $backendPath -DbUrl $resolvedDbUrl
  Set-EnvValue -Path $backendEnv -Key "DATABASE_URL" -Value $resolvedDbUrl
}

if ($InitDatabase) {
  Write-Host "[INIT] ensure target database exists"
  Ensure-DatabaseExists -PythonExe $venvPython -BackendPath $backendPath -DbUrl $resolvedDbUrl
}

if ($CorsOriginsJson) {
  Set-EnvValue -Path $backendEnv -Key "CORS_ORIGINS" -Value $CorsOriginsJson
}
else {
  $origins = @("http://localhost:$FrontendPort", "http://127.0.0.1:$FrontendPort")
  $ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object {
    $_.IPAddress -notlike "169.254.*" -and $_.IPAddress -ne "127.0.0.1"
  } | Select-Object -ExpandProperty IPAddress -Unique
  foreach ($ip in $ips) {
    $origins += "http://${ip}:$FrontendPort"
  }
  $originItems = @($origins | Select-Object -Unique)
  $quotedOrigins = $originItems | ForEach-Object { '"' + $_.Replace('"', '\"') + '"' }
  $corsJson = "[" + ($quotedOrigins -join ",") + "]"
  Set-EnvValue -Path $backendEnv -Key "CORS_ORIGINS" -Value $corsJson
}

if ($PrebuiltFrontendDist) {
  Ensure-PathExists -Path $PrebuiltFrontendDist -Label "PrebuiltFrontendDist"
  Ensure-PathExists -Path (Join-Path $PrebuiltFrontendDist "index.html") -Label "PrebuiltFrontendDist/index.html"
  if (Test-Path $frontendDist) {
    Remove-Item -Path $frontendDist -Recurse -Force
  }
  Copy-Item $PrebuiltFrontendDist $frontendDist -Recurse -Force
  Write-Host "[INIT] frontend dist copied from prebuilt directory"
}
else {
  if (-not $ApiBaseUrl) {
    $ApiBaseUrl = "http://127.0.0.1:$BackendPort/api/v1"
  }
  @(
    "VITE_API_BASE_URL=$ApiBaseUrl"
    "VITE_USER_ID=prod_user"
    "VITE_USER_ROLE=ADMIN"
    "VITE_USER_DEPT="
  ) | Set-Content -Path $frontendEnvProd -Encoding UTF8

  Push-Location $frontendPath
  try {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
      throw "npm not found. Install Node.js or use -PrebuiltFrontendDist."
    }
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
}

if (-not (Test-Path $serviceEnv)) {
  Copy-Item $serviceEnvExample $serviceEnv -Force
}
Set-EnvValue -Path $serviceEnv -Key "BACKEND_PORT" -Value "$BackendPort"
Set-EnvValue -Path $serviceEnv -Key "FRONTEND_PORT" -Value "$FrontendPort"

if ($SeedData) {
  if (-not $SeedDataDir) {
    throw "SeedData=true but SeedDataDir is empty."
  }
  Write-Host "[INIT] import seed data from $SeedDataDir"
  Import-SeedData -PythonExe $venvPython -BackendPath $backendPath -SeedDir $SeedDataDir
}

if ($OpenFirewall) {
  Ensure-FirewallRule -Name "DiseaseAnalytics-Backend-$BackendPort" -Port $BackendPort
  Ensure-FirewallRule -Name "DiseaseAnalytics-Frontend-$FrontendPort" -Port $FrontendPort
}

if ($InstallServices) {
  Repair-InstallServicesScript -OpsWinPath $opsWinPath
  & (Join-Path $opsWinPath "install_services.ps1") -ProjectRoot $ProjectRoot -BackendPort $BackendPort -FrontendPort $FrontendPort -StartNow
}

$ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object {
  $_.IPAddress -notlike "169.254.*" -and $_.IPAddress -ne "127.0.0.1"
} | Select-Object -ExpandProperty IPAddress -Unique

Write-Host ""
Write-Host "Deployment completed."
Write-Host "Backend health: http://127.0.0.1:$BackendPort/api/v1/health"
Write-Host "Frontend local: http://127.0.0.1:$FrontendPort"
foreach ($ip in $ips) {
  Write-Host "Frontend LAN  : http://${ip}:$FrontendPort"
}
