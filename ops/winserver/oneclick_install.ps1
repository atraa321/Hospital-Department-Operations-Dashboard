param(
  [string]$ConfigPath = ""
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

function To-Bool {
  param(
    [Parameter(Mandatory = $false)]$Value,
    [bool]$Default = $false
  )

  if ($null -eq $Value) {
    return $Default
  }
  if ($Value -is [bool]) {
    return $Value
  }
  $text = "$Value".Trim().ToLowerInvariant()
  if ($text -in @("1", "true", "yes", "y", "on")) {
    return $true
  }
  if ($text -in @("0", "false", "no", "n", "off")) {
    return $false
  }
  return $Default
}

function Resolve-PythonCommand {
  param(
    [string]$ConfiguredPythonCommand = ""
  )

  if ($ConfiguredPythonCommand) {
    $cmd = Get-Command $ConfiguredPythonCommand -ErrorAction SilentlyContinue
    if (-not $cmd) {
      throw "Configured PythonCommand not found: $ConfiguredPythonCommand"
    }
    return $ConfiguredPythonCommand
  }

  foreach ($candidate in @("py", "python", "python3")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
      return $candidate
    }
  }

  throw "Python runtime not found. Install Python 3.12+ or set PythonCommand in deploy.config.psd1."
}

function Invoke-RobocopyMirror {
  param(
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$Destination
  )

  Ensure-PathExists -Path $Source -Label "project source"
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
  & robocopy @args | Out-Null
  if ($LASTEXITCODE -gt 7) {
    throw "robocopy failed with exit code $LASTEXITCODE"
  }
}

function Invoke-RobocopyExactMirror {
  param(
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$Destination
  )

  Ensure-PathExists -Path $Source -Label "source directory"
  if (-not (Test-Path $Destination)) {
    New-Item -Path $Destination -ItemType Directory | Out-Null
  }

  $args = @(
    $Source
    $Destination
    "/MIR"
    "/R:1"
    "/W:1"
    "/NFL"
    "/NDL"
    "/NJH"
    "/NJS"
    "/NP"
  )
  & robocopy @args | Out-Null
  if ($LASTEXITCODE -gt 7) {
    throw "robocopy mirror failed with exit code $LASTEXITCODE"
  }
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

  throw "$ExeName not found. Install MySQL client tools or set MySqlBinDir in deploy.config.psd1."
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
    throw "DatabaseUrl must be mysql://... or mysql+driver://..."
  }

  try {
    $uri = [System.Uri]$normalized
  }
  catch {
    throw "Invalid DatabaseUrl format."
  }

  if (-not $uri.Host) {
    throw "DatabaseUrl missing host."
  }
  if (-not $uri.UserInfo) {
    throw "DatabaseUrl missing user info."
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
    throw "DatabaseUrl missing database name."
  }

  return @{
    Host = $uri.Host
    Port = if ($uri.Port -gt 0) { $uri.Port } else { 3306 }
    User = $username
    Password = $password
    Database = $database
  }
}

function Restore-DatabaseFromSql {
  param(
    [Parameter(Mandatory = $true)][string]$DatabaseUrl,
    [Parameter(Mandatory = $true)][string]$SqlFile,
    [string]$MySqlBinDir = ""
  )

  Ensure-PathExists -Path $SqlFile -Label "snapshot SQL file"
  $conn = Parse-MySqlConnectionInfoFromUrl -DatabaseUrl $DatabaseUrl
  $mysqlExe = Resolve-MySqlExecutable -ExeName "mysql.exe" -PreferredBinDir $MySqlBinDir

  $stderrPath = "$SqlFile.restore.stderr.log"
  if (Test-Path $stderrPath) {
    Remove-Item -Path $stderrPath -Force
  }

  $args = @(
    "-h", $conn.Host,
    "-P", "$($conn.Port)",
    "-u$($conn.User)",
    "--default-character-set=utf8mb4",
    $conn.Database
  )
  if ($conn.Password -ne "") {
    $args += "-p$($conn.Password)"
  }

  $proc = Start-Process -FilePath $mysqlExe -ArgumentList $args -NoNewWindow -Wait -PassThru `
    -RedirectStandardInput $SqlFile -RedirectStandardError $stderrPath

  if ($proc.ExitCode -ne 0) {
    $tail = ""
    if (Test-Path $stderrPath) {
      $tail = (Get-Content -Path $stderrPath -Tail 30) -join [Environment]::NewLine
    }
    throw "mysql restore failed with exit code $($proc.ExitCode). $tail"
  }

  if (Test-Path $stderrPath) {
    Remove-Item -Path $stderrPath -Force -ErrorAction SilentlyContinue
  }
}

function Stop-ServiceIfExists {
  param(
    [Parameter(Mandatory = $true)][string]$Name
  )

  $svc = Get-Service -Name $Name -ErrorAction SilentlyContinue
  if (-not $svc) {
    return
  }
  if ($svc.Status -eq "Stopped") {
    return
  }

  Write-Host "[INFO] stopping service: $Name"
  Stop-Service -Name $Name -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 2
}

function Test-Admin {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($identity)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

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

function Ensure-ServiceDirect {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$DisplayName,
    [Parameter(Mandatory = $true)][string]$Description,
    [Parameter(Mandatory = $true)][string]$BinPath
  )

  $svc = Get-Service -Name $Name -ErrorAction SilentlyContinue
  if ($svc) {
    if ($svc.Status -ne "Stopped") {
      sc.exe stop $Name | Out-Null
      Start-Sleep -Seconds 2
    }
    sc.exe config $Name binPath= "$BinPath" start= auto | Out-Null
  }
  else {
    sc.exe create $Name binPath= "$BinPath" start= auto DisplayName= "$DisplayName" | Out-Null
  }

  sc.exe description $Name "$Description" | Out-Null
  sc.exe failure $Name reset= 86400 actions= restart/5000/restart/5000/restart/5000 | Out-Null
}

function Install-ServicesDirect {
  param(
    [Parameter(Mandatory = $true)][string]$ProjectRoot,
    [Parameter(Mandatory = $true)][int]$BackendPort,
    [Parameter(Mandatory = $true)][int]$FrontendPort,
    [string]$BackendServiceName = "DiseaseAnalyticsBackend",
    [string]$FrontendServiceName = "DiseaseAnalyticsFrontend",
    [switch]$StartNow = $true
  )

  if (-not (Test-Admin)) {
    throw "Please run as Administrator to install services."
  }

  $opsWinPath = Join-Path $ProjectRoot "ops\winserver"
  $backendCmd = Join-Path $opsWinPath "run_backend.cmd"
  $frontendCmd = Join-Path $opsWinPath "run_frontend.cmd"
  $serviceEnv = Join-Path $opsWinPath "service.env"
  $serviceEnvExample = Join-Path $opsWinPath "service.env.example"

  Ensure-PathExists -Path $backendCmd -Label "run_backend.cmd"
  Ensure-PathExists -Path $frontendCmd -Label "run_frontend.cmd"
  Ensure-PathExists -Path $serviceEnvExample -Label "service.env.example"

  if (-not (Test-Path $serviceEnv)) {
    Copy-Item $serviceEnvExample $serviceEnv -Force
  }

  Set-EnvValue -Path $serviceEnv -Key "BACKEND_PORT" -Value "$BackendPort"
  Set-EnvValue -Path $serviceEnv -Key "FRONTEND_PORT" -Value "$FrontendPort"

  $backendBinPath = "cmd.exe /c `"`"$backendCmd`"`""
  $frontendBinPath = "cmd.exe /c `"`"$frontendCmd`"`""

  Ensure-ServiceDirect -Name $BackendServiceName -DisplayName "Disease Analytics Backend" -Description "FastAPI backend service for Disease Analytics." -BinPath $backendBinPath
  Ensure-ServiceDirect -Name $FrontendServiceName -DisplayName "Disease Analytics Frontend" -Description "Static frontend service for Disease Analytics." -BinPath $frontendBinPath

  if ($StartNow) {
    sc.exe start $BackendServiceName | Out-Null
    Start-Sleep -Seconds 2
    sc.exe start $FrontendServiceName | Out-Null
  }
}

function Repair-InstallServicesScript {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [string]$FallbackPath = ""
  )

  if (-not (Test-Path $Path)) {
    return
  }

  $text = Get-Content -Path $Path -Raw
  $normalized = $text `
    -replace [char]0x201C, '"' `
    -replace [char]0x201D, '"' `
    -replace [char]0x2018, "'" `
    -replace [char]0x2019, "'" `
    -replace [char]0xFF02, '"' `
    -replace [char]0xFF07, "'" `
    -replace [char]0x300C, '"' `
    -replace [char]0x300D, '"' `
    -replace [char]0x300E, '"' `
    -replace [char]0x300F, '"' `
    -replace [char]0xFF5B, '{' `
    -replace [char]0xFF5D, '}' `
    -replace [char]0xFF08, '(' `
    -replace [char]0xFF09, ')' `
    -replace [char]0x2013, '-' `
    -replace [char]0x2014, '-'

  if ($normalized -ne $text) {
    Set-Content -Path $Path -Value $normalized -Encoding UTF8
    Write-Host "[INFO] install_services.ps1 quotes normalized."
  }

  $parseOk = $false
  try {
    [void][System.Management.Automation.ScriptBlock]::Create((Get-Content -Path $Path -Raw))
    $parseOk = $true
  }
  catch {
    $parseOk = $false
  }

  if (-not $parseOk -and $FallbackPath -and (Test-Path $FallbackPath)) {
    Copy-Item -Path $FallbackPath -Destination $Path -Force
    Write-Host "[WARN] install_services.ps1 parse failed, replaced by bundled fallback copy."
    try {
      [void][System.Management.Automation.ScriptBlock]::Create((Get-Content -Path $Path -Raw))
      $parseOk = $true
    }
    catch {
      $parseOk = $false
    }
  }

  return $parseOk
}

$bundleRoot = $PSScriptRoot
if (-not $ConfigPath) {
  $ConfigPath = Join-Path $bundleRoot "deploy.config.psd1"
}

Ensure-PathExists -Path $ConfigPath -Label "deploy config"
$config = Import-PowerShellDataFile -Path $ConfigPath

$sourceRoot = Join-Path $bundleRoot "project_source"
$wheelhouse = Join-Path $bundleRoot "python_wheels"
$frontendDist = Join-Path $bundleRoot "frontend_dist"

Ensure-PathExists -Path $sourceRoot -Label "project_source directory"
Ensure-PathExists -Path $wheelhouse -Label "python_wheels directory"
Ensure-PathExists -Path (Join-Path $frontendDist "index.html") -Label "frontend_dist/index.html"

$projectRoot = [string]$config.ProjectRoot
$databaseUrl = [string]$config.DatabaseUrl
$pythonCommandConfigured = [string]$config.PythonCommand
$pythonVersion = [string]$config.PythonVersion
$backendPort = [int]$config.BackendPort
$frontendPort = [int]$config.FrontendPort
$apiBaseUrl = [string]$config.ApiBaseUrl
$corsOriginsJson = [string]$config.CorsOriginsJson
$installServices = To-Bool -Value $config.InstallServices -Default $true
$openFirewall = To-Bool -Value $config.OpenFirewall -Default $true
$initDatabase = To-Bool -Value $config.InitDatabase -Default $true
$seedData = To-Bool -Value $config.SeedData -Default $false
$restoreSnapshot = To-Bool -Value $config.RestoreSnapshot -Default $false
$restoreUploads = To-Bool -Value $config.RestoreUploads -Default $true
$mySqlBinDir = [string]$config.MySqlBinDir
$seedDataDirName = [string]$config.SeedDataDirName
if (-not $seedDataDirName) {
  $seedDataDirName = "seed_data"
}
$snapshotSqlRelativePath = [string]$config.SnapshotSqlRelativePath
if (-not $snapshotSqlRelativePath) {
  $snapshotSqlRelativePath = "data_snapshot\database.sql"
}
$snapshotUploadsRelativePath = [string]$config.SnapshotUploadsRelativePath
if (-not $snapshotUploadsRelativePath) {
  $snapshotUploadsRelativePath = "data_snapshot\uploads"
}
$uploadDirRelativePath = [string]$config.UploadDirRelativePath
if (-not $uploadDirRelativePath) {
  $uploadDirRelativePath = "backend\data\uploads"
}

if (-not $projectRoot) {
  throw "ProjectRoot is empty in config."
}
if (-not $databaseUrl) {
  throw "DatabaseUrl is empty in config."
}
if (-not $pythonVersion) {
  $pythonVersion = "3.12"
}

$pythonCommand = Resolve-PythonCommand -ConfiguredPythonCommand $pythonCommandConfigured

Write-Host "[1/4] Sync project files to $projectRoot"
Invoke-RobocopyMirror -Source $sourceRoot -Destination $projectRoot

$deployScript = Join-Path $projectRoot "ops\winserver\deploy_winserver.ps1"
Ensure-PathExists -Path $deployScript -Label "deploy script"

$seedDataDir = ""
if ($seedData) {
  $seedDataDir = Join-Path $bundleRoot $seedDataDirName
  Ensure-PathExists -Path $seedDataDir -Label "seed data directory"
}

$installServicesInDeploy = $false

Write-Host "[2/4] Run deployment"
$deployParams = @{
  ProjectRoot = $projectRoot
  PythonCommand = $pythonCommand
  PythonVersion = $pythonVersion
  WheelhouseDir = $wheelhouse
  PrebuiltFrontendDist = $frontendDist
  DatabaseUrl = $databaseUrl
  BackendPort = $backendPort
  FrontendPort = $frontendPort
  InstallServices = $installServicesInDeploy
  OpenFirewall = $openFirewall
  InitDatabase = $initDatabase
  SeedData = $seedData
}
if ($apiBaseUrl) {
  $deployParams["ApiBaseUrl"] = $apiBaseUrl
}
if ($corsOriginsJson) {
  $deployParams["CorsOriginsJson"] = $corsOriginsJson
}
if ($seedData -and $seedDataDir) {
  $deployParams["SeedDataDir"] = $seedDataDir
}

& $deployScript @deployParams

Write-Host "[3/4] Restore current data snapshot"
if ($restoreSnapshot) {
  $snapshotSqlPath = Join-Path $bundleRoot $snapshotSqlRelativePath
  Ensure-PathExists -Path $snapshotSqlPath -Label "snapshot SQL path"

  Stop-ServiceIfExists -Name "DiseaseAnalyticsBackend"
  Stop-ServiceIfExists -Name "DiseaseAnalyticsFrontend"

  Restore-DatabaseFromSql -DatabaseUrl $databaseUrl -SqlFile $snapshotSqlPath -MySqlBinDir $mySqlBinDir
  Write-Host "[OK] database restored from snapshot: $snapshotSqlPath"

  if ($restoreUploads) {
    $snapshotUploadsPath = Join-Path $bundleRoot $snapshotUploadsRelativePath
    if (Test-Path $snapshotUploadsPath) {
      $targetUploadPath = Join-Path $projectRoot $uploadDirRelativePath
      Invoke-RobocopyExactMirror -Source $snapshotUploadsPath -Destination $targetUploadPath
      Write-Host "[OK] upload files restored to: $targetUploadPath"
    }
    else {
      Write-Host "[WARN] restoreUploads=true but snapshot uploads path not found: $snapshotUploadsPath"
    }
  }
}
else {
  Write-Host "[INFO] snapshot restore skipped."
}

Write-Host "[4/4] Finalize services"
if ($installServices) {
  $installServicesScript = Join-Path $projectRoot "ops\winserver\install_services.ps1"
  $installServicesFallback = Join-Path $bundleRoot "project_source\ops\winserver\install_services.ps1"
  $scriptInstalled = $false

  if (Test-Path $installServicesScript) {
    $scriptReady = Repair-InstallServicesScript -Path $installServicesScript -FallbackPath $installServicesFallback
    if ($scriptReady) {
      try {
        & $installServicesScript -ProjectRoot $projectRoot -BackendPort $backendPort -FrontendPort $frontendPort -StartNow
        $scriptInstalled = $true
      }
      catch {
        Write-Host "[WARN] install_services.ps1 execution failed, fallback to direct service install."
      }
    }
    else {
      Write-Host "[WARN] install_services.ps1 parse failed after repair, fallback to direct service install."
    }
  }
  else {
    Write-Host "[WARN] install_services.ps1 missing, fallback to direct service install."
  }

  if (-not $scriptInstalled) {
    Install-ServicesDirect -ProjectRoot $projectRoot -BackendPort $backendPort -FrontendPort $frontendPort -StartNow
    Write-Host "[OK] services installed by direct fallback."
  }
}

Write-Host "One-click deployment finished."
Write-Host "Backend: http://127.0.0.1:$backendPort/api/v1/health"
Write-Host "Frontend: http://127.0.0.1:$frontendPort"
