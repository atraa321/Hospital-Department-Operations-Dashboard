param(
  [string]$ProjectRoot = "D:\病种分析V2",
  [string]$BackendServiceName = "DiseaseAnalyticsBackend",
  [string]$FrontendServiceName = "DiseaseAnalyticsFrontend",
  [int]$BackendPort = 18080,
  [int]$FrontendPort = 5173,
  [switch]$StartNow = $true
)

$ErrorActionPreference = "Stop"

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

function Ensure-Service {
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

if (-not (Test-Admin)) {
  throw "请使用管理员权限运行本脚本。"
}

$opsWinPath = Join-Path $ProjectRoot "ops\winserver"
$backendCmd = Join-Path $opsWinPath "run_backend.cmd"
$frontendCmd = Join-Path $opsWinPath "run_frontend.cmd"
$serviceEnv = Join-Path $opsWinPath "service.env"
$serviceEnvExample = Join-Path $opsWinPath "service.env.example"

if (-not (Test-Path $backendCmd)) {
  throw "文件不存在: $backendCmd"
}
if (-not (Test-Path $frontendCmd)) {
  throw "文件不存在: $frontendCmd"
}
if (-not (Test-Path $serviceEnv)) {
  if (-not (Test-Path $serviceEnvExample)) {
    throw "文件不存在: $serviceEnvExample"
  }
  Copy-Item $serviceEnvExample $serviceEnv -Force
}

Set-EnvValue -Path $serviceEnv -Key "BACKEND_PORT" -Value "$BackendPort"
Set-EnvValue -Path $serviceEnv -Key "FRONTEND_PORT" -Value "$FrontendPort"

$backendBinPath = "cmd.exe /c `"`"$backendCmd`"`""
$frontendBinPath = "cmd.exe /c `"`"$frontendCmd`"`""

Ensure-Service -Name $BackendServiceName -DisplayName "Disease Analytics Backend" -Description "FastAPI backend service for Disease Analytics." -BinPath $backendBinPath
Ensure-Service -Name $FrontendServiceName -DisplayName "Disease Analytics Frontend" -Description "Static frontend service for Disease Analytics." -BinPath $frontendBinPath

if ($StartNow) {
  sc.exe start $BackendServiceName | Out-Null
  Start-Sleep -Seconds 2
  sc.exe start $FrontendServiceName | Out-Null
}

Write-Host "Services installed/updated:"
Write-Host "- $BackendServiceName"
Write-Host "- $FrontendServiceName"
