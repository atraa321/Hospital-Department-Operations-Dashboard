param(
  [string]$ProjectRoot = "D:\病种分析V2",
  [string]$OutputDir = "D:\deploy\oneclick-bundles",
  [string]$PythonCommand = "py",
  [string]$PythonVersion = "3.12",
  [string]$ApiBaseUrl = "http://127.0.0.1:18080/api/v1",
  [bool]$IncludeSeedData = $true,
  [string]$SeedDataPath = "",
  [bool]$IncludeCurrentData = $false,
  [string]$CurrentDataSqlFile = "",
  [string]$CurrentDatabaseUrl = "",
  [string]$MySqlBinDir = "",
  [bool]$IncludeUploads = $true,
  [string]$CurrentUploadsDir = ""
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

function Invoke-RobocopyCopy {
  param(
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$Destination,
    [string[]]$ExcludeDirs = @(),
    [string[]]$ExcludeFiles = @()
  )

  if (-not (Test-Path $Destination)) {
    New-Item -Path $Destination -ItemType Directory | Out-Null
  }

  $args = @(
    $Source
    $Destination
    "/E"
    "/R:1"
    "/W:1"
    "/NFL"
    "/NDL"
    "/NJH"
    "/NJS"
    "/NP"
  )
  if ($ExcludeDirs.Count -gt 0) {
    $args += "/XD"
    $args += $ExcludeDirs
  }
  if ($ExcludeFiles.Count -gt 0) {
    $args += "/XF"
    $args += $ExcludeFiles
  }

  & robocopy @args | Out-Null
  if ($LASTEXITCODE -gt 7) {
    throw "robocopy failed with exit code $LASTEXITCODE"
  }
}

function Set-Psd1Value {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][string]$Key,
    [Parameter(Mandatory = $true)][string]$RawValue
  )

  $lines = @()
  if (Test-Path $Path) {
    $lines = Get-Content -Path $Path
  }
  $pattern = "^\s*" + [Regex]::Escape($Key) + "\s*="
  $updated = $false
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match $pattern) {
      $lines[$i] = "  $Key = $RawValue"
      $updated = $true
      break
    }
  }
  if (-not $updated) {
    $lines += "  $Key = $RawValue"
  }
  Set-Content -Path $Path -Value $lines -Encoding UTF8
}

function Resolve-MySqlExecutable {
  param(
    [Parameter(Mandatory = $true)][string]$ExeName,
    [string]$PreferredBinDir = ""
  )

  if ($PreferredBinDir) {
    $candidate = Join-Path $PreferredBinDir $ExeName
    if (Test-Path $candidate) {
      return (Resolve-Path $candidate).Path
    }
    throw "$ExeName not found in MySqlBinDir: $PreferredBinDir"
  }

  $cmd = Get-Command $ExeName -ErrorAction SilentlyContinue
  if ($cmd) {
    return $cmd.Source
  }

  $roots = @(
    "C:\Program Files\MySQL",
    "C:\Program Files (x86)\MySQL"
  )
  foreach ($root in $roots) {
    if (-not (Test-Path $root)) {
      continue
    }
    $dirs = Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending
    foreach ($dir in $dirs) {
      $candidate = Join-Path $dir.FullName ("bin\" + $ExeName)
      if (Test-Path $candidate) {
        return (Resolve-Path $candidate).Path
      }
    }
  }

  throw "$ExeName not found. Install MySQL client tools or pass -MySqlBinDir."
}

function Parse-MySqlConnectionInfoFromUrl {
  param(
    [Parameter(Mandatory = $true)][string]$DatabaseUrl
  )

  $normalized = $DatabaseUrl.Trim()
  if ($normalized -match "^mysql\+[^:]+://") {
    $normalized = $normalized -replace "^mysql\+[^:]+://", "mysql://"
  }
  if ($normalized -notmatch "^mysql://") {
    throw "CurrentDatabaseUrl must be mysql://... or mysql+driver://..."
  }

  try {
    $uri = [System.Uri]$normalized
  }
  catch {
    throw "Invalid CurrentDatabaseUrl: $DatabaseUrl"
  }

  if (-not $uri.Host) {
    throw "CurrentDatabaseUrl missing host."
  }
  if (-not $uri.UserInfo) {
    throw "CurrentDatabaseUrl missing user info."
  }

  $userInfo = $uri.UserInfo.Split(":", 2)
  $username = [System.Uri]::UnescapeDataString($userInfo[0])
  $password = ""
  if ($userInfo.Count -gt 1) {
    $password = [System.Uri]::UnescapeDataString($userInfo[1])
  }

  $database = $uri.AbsolutePath.Trim("/")
  if ($database.Contains("/")) {
    $database = $database.Split("/")[0]
  }
  if ($database.Contains("?")) {
    $database = $database.Split("?")[0]
  }
  if (-not $database) {
    throw "CurrentDatabaseUrl missing database name."
  }

  return @{
    Host = $uri.Host
    Port = if ($uri.Port -gt 0) { $uri.Port } else { 3306 }
    User = $username
    Password = $password
    Database = $database
  }
}

function Export-CurrentDatabase {
  param(
    [Parameter(Mandatory = $true)][string]$OutputSqlFile,
    [Parameter(Mandatory = $true)][string]$DatabaseUrl,
    [string]$PreferredMySqlBinDir = ""
  )

  $conn = Parse-MySqlConnectionInfoFromUrl -DatabaseUrl $DatabaseUrl
  $mysqldumpExe = Resolve-MySqlExecutable -ExeName "mysqldump.exe" -PreferredBinDir $PreferredMySqlBinDir

  if (Test-Path $OutputSqlFile) {
    Remove-Item -Path $OutputSqlFile -Force
  }
  $stderrPath = "$OutputSqlFile.stderr.log"
  if (Test-Path $stderrPath) {
    Remove-Item -Path $stderrPath -Force
  }

  $args = @(
    "-h", $conn.Host,
    "-P", "$($conn.Port)",
    "-u$($conn.User)",
    "--single-transaction",
    "--routines",
    "--events",
    "--set-gtid-purged=OFF",
    "--default-character-set=utf8mb4",
    $conn.Database
  )
  if ($conn.Password -ne "") {
    $args += "-p$($conn.Password)"
  }

  $proc = Start-Process -FilePath $mysqldumpExe -ArgumentList $args -NoNewWindow -Wait -PassThru `
    -RedirectStandardOutput $OutputSqlFile -RedirectStandardError $stderrPath

  if ($proc.ExitCode -ne 0) {
    $tail = ""
    if (Test-Path $stderrPath) {
      $tail = (Get-Content -Path $stderrPath -Tail 30) -join [Environment]::NewLine
    }
    throw "mysqldump failed with exit code $($proc.ExitCode). $tail"
  }

  if (Test-Path $stderrPath) {
    Remove-Item -Path $stderrPath -Force -ErrorAction SilentlyContinue
  }
}

Ensure-PathExists -Path $ProjectRoot -Label "ProjectRoot"

$backendPath = Join-Path $ProjectRoot "backend"
$frontendPath = Join-Path $ProjectRoot "frontend"
$opsPath = Join-Path $ProjectRoot "ops\winserver"
$requirementsPath = Join-Path $backendPath "requirements.txt"
$frontendEnvProd = Join-Path $frontendPath ".env.production.local"

Ensure-PathExists -Path $backendPath -Label "backend directory"
Ensure-PathExists -Path $frontendPath -Label "frontend directory"
Ensure-PathExists -Path $opsPath -Label "ops\\winserver directory"
Ensure-PathExists -Path $requirementsPath -Label "backend requirements.txt"
Ensure-PathExists -Path (Join-Path $opsPath "deploy_winserver.ps1") -Label "deploy_winserver.ps1"
Ensure-PathExists -Path (Join-Path $opsPath "oneclick_install.ps1") -Label "oneclick_install.ps1"
Ensure-PathExists -Path (Join-Path $opsPath "oneclick_install.bat") -Label "oneclick_install.bat"
Ensure-PathExists -Path (Join-Path $opsPath "deploy.config.template.psd1") -Label "deploy.config.template.psd1"

if ($IncludeSeedData -and -not $SeedDataPath) {
  $SeedDataPath = Join-Path $ProjectRoot "基础数据"
}
if ($IncludeSeedData) {
  Ensure-PathExists -Path $SeedDataPath -Label "SeedDataPath"
}

if ($IncludeCurrentData) {
  if (-not $CurrentDataSqlFile -and -not $CurrentDatabaseUrl) {
    throw "IncludeCurrentData=true requires CurrentDataSqlFile or CurrentDatabaseUrl."
  }
  if ($CurrentDataSqlFile) {
    Ensure-PathExists -Path $CurrentDataSqlFile -Label "CurrentDataSqlFile"
  }
  if ($IncludeUploads -and -not $CurrentUploadsDir) {
    $CurrentUploadsDir = Join-Path $backendPath "data\uploads"
  }
}

$shouldCopyUploads = $false
if ($IncludeCurrentData -and $IncludeUploads -and $CurrentUploadsDir) {
  if (Test-Path $CurrentUploadsDir) {
    $shouldCopyUploads = $true
  }
  else {
    Write-Host "[WARN] CurrentUploadsDir not found, skip upload snapshot: $CurrentUploadsDir"
  }
}

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$bundleRoot = Join-Path $OutputDir "disease_analytics_oneclick_$ts"
$wheelDir = Join-Path $bundleRoot "python_wheels"
$distDir = Join-Path $bundleRoot "frontend_dist"
$sourceDir = Join-Path $bundleRoot "project_source"
$seedDir = Join-Path $bundleRoot "seed_data"
$snapshotDir = Join-Path $bundleRoot "data_snapshot"
$snapshotSql = Join-Path $snapshotDir "database.sql"
$snapshotUploads = Join-Path $snapshotDir "uploads"
$zipPath = "$bundleRoot.zip"

if (-not (Test-Path $OutputDir)) {
  New-Item -Path $OutputDir -ItemType Directory | Out-Null
}
New-Item -Path $bundleRoot -ItemType Directory | Out-Null
New-Item -Path $wheelDir -ItemType Directory | Out-Null
New-Item -Path $distDir -ItemType Directory | Out-Null
New-Item -Path $sourceDir -ItemType Directory | Out-Null

Write-Host "[1/7] Download backend wheels"
Invoke-Python -Args @("-m", "pip", "download", "-r", $requirementsPath, "-d", $wheelDir)

Write-Host "[2/7] Build frontend dist"
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

Write-Host "[3/7] Copy project source"
$excludeDirs = @(
  (Join-Path $ProjectRoot ".git"),
  (Join-Path $ProjectRoot ".pytest_cache"),
  (Join-Path $ProjectRoot "frontend\node_modules"),
  (Join-Path $ProjectRoot "frontend\dist"),
  (Join-Path $ProjectRoot "backend\.venv312"),
  (Join-Path $ProjectRoot "backend\data\uploads_test_tmp"),
  (Join-Path $ProjectRoot "logs")
)
Invoke-RobocopyCopy -Source $ProjectRoot -Destination $sourceDir -ExcludeDirs $excludeDirs -ExcludeFiles @("*.pyc")

Write-Host "[4/7] Copy frontend dist and one-click entry files"
Copy-Item (Join-Path $frontendPath "dist\*") $distDir -Recurse -Force
Copy-Item (Join-Path $opsPath "oneclick_install.ps1") (Join-Path $bundleRoot "oneclick_install.ps1") -Force
Copy-Item (Join-Path $opsPath "oneclick_install.bat") (Join-Path $bundleRoot "oneclick_install.bat") -Force
$bundleConfigPath = Join-Path $bundleRoot "deploy.config.psd1"
Copy-Item (Join-Path $opsPath "deploy.config.template.psd1") $bundleConfigPath -Force
@(
  "@echo off"
  "setlocal EnableExtensions"
  "set SCRIPT_DIR=%~dp0"
  "powershell -NoProfile -ExecutionPolicy Bypass -File ""%SCRIPT_DIR%oneclick_install.ps1"""
  "set EXIT_CODE=%ERRORLEVEL%"
  "if not ""%EXIT_CODE%""==""0"" ("
  "  echo."
  "  echo [ERROR] Deployment failed, exit code: %EXIT_CODE%"
  "  pause"
  ")"
  "exit /b %EXIT_CODE%"
) | Set-Content -Path (Join-Path $bundleRoot "一键部署_病种分析系统.bat") -Encoding ASCII

if ($IncludeCurrentData) {
  Write-Host "[5/7] Package current data snapshot"
  New-Item -Path $snapshotDir -ItemType Directory | Out-Null
  if ($CurrentDataSqlFile) {
    Copy-Item -Path $CurrentDataSqlFile -Destination $snapshotSql -Force
  }
  else {
    Export-CurrentDatabase -OutputSqlFile $snapshotSql -DatabaseUrl $CurrentDatabaseUrl -PreferredMySqlBinDir $MySqlBinDir
  }

  if ($shouldCopyUploads) {
    Invoke-RobocopyCopy -Source $CurrentUploadsDir -Destination $snapshotUploads
  }
  else {
    Write-Host "[INFO] upload snapshot skipped."
  }

  Set-Psd1Value -Path $bundleConfigPath -Key "RestoreSnapshot" -RawValue '$true'
  Set-Psd1Value -Path $bundleConfigPath -Key "RestoreUploads" -RawValue ($(if ($shouldCopyUploads) { '$true' } else { '$false' }))
}
else {
  Write-Host "[5/7] Skip current data snapshot"
}

if ($IncludeSeedData) {
  Write-Host "[6/7] Copy seed data"
  Invoke-RobocopyCopy -Source $SeedDataPath -Destination $seedDir
}
else {
  Write-Host "[6/7] Skip seed data copy"
}

@(
  "bundle_created_at=$ts"
  "project_root_source=$ProjectRoot"
  "api_base_url=$ApiBaseUrl"
  "python_version=$PythonVersion"
  "include_seed_data=$IncludeSeedData"
  "include_current_data=$IncludeCurrentData"
  "include_upload_snapshot=$shouldCopyUploads"
  "current_upload_source=$CurrentUploadsDir"
) | Set-Content -Path (Join-Path $bundleRoot "bundle_manifest.txt") -Encoding UTF8

Write-Host "[7/7] Create zip package"
if (Test-Path $zipPath) {
  Remove-Item $zipPath -Force
}
Compress-Archive -Path (Join-Path $bundleRoot "*") -DestinationPath $zipPath -CompressionLevel Optimal

Write-Host "One-click bundle ready:"
Write-Host "- Folder: $bundleRoot"
Write-Host "- Zip   : $zipPath"
