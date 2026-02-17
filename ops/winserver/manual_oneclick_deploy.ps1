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

$scriptDir = $PSScriptRoot
if (-not $ConfigPath) {
  $ConfigPath = Join-Path $scriptDir "manual_deploy.config.psd1"
}

Ensure-PathExists -Path $ConfigPath -Label "manual deploy config"
$config = Import-PowerShellDataFile -Path $ConfigPath

$entry = Join-Path $scriptDir "manual_deploy_min.ps1"
Ensure-PathExists -Path $entry -Label "manual_deploy_min.ps1"

$projectRoot = [string]$config.ProjectRoot
$fallbackProjectRoot = (Resolve-Path (Join-Path $scriptDir "..\\..")).Path
if (-not $projectRoot) {
  $projectRoot = $fallbackProjectRoot
}
elseif (-not (Test-Path $projectRoot)) {
  Write-Host "[WARN] Config ProjectRoot not found, fallback to script root: $fallbackProjectRoot"
  $projectRoot = $fallbackProjectRoot
}

$params = @{
  ProjectRoot = $projectRoot
  DatabaseUrl = [string]$config.DatabaseUrl
  BackendPort = [int]$config.BackendPort
  FrontendPort = [int]$config.FrontendPort
  PythonCommand = [string]$config.PythonCommand
  PythonVersion = [string]$config.PythonVersion
  WheelhouseDir = [string]$config.WheelhouseDir
  PrebuiltFrontendDist = [string]$config.PrebuiltFrontendDist
  InitDatabase = [bool]$config.InitDatabase
  SeedData = [bool]$config.SeedData
  SeedDataDir = [string]$config.SeedDataDir
  InstallServices = [bool]$config.InstallServices
  OpenFirewall = [bool]$config.OpenFirewall
}

& $entry @params
