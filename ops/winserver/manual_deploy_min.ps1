param(
  [string]$ProjectRoot = "D:\病种分析V2",
  [Parameter(Mandatory = $true)][string]$DatabaseUrl,
  [int]$BackendPort = 18080,
  [int]$FrontendPort = 5173,
  [string]$PythonCommand = "",
  [string]$PythonVersion = "3.12",
  [string]$WheelhouseDir = "",
  [string]$PrebuiltFrontendDist = "",
  [bool]$InitDatabase = $true,
  [bool]$SeedData = $false,
  [string]$SeedDataDir = "",
  [bool]$InstallServices = $true,
  [bool]$OpenFirewall = $true
)

$ErrorActionPreference = "Stop"

function Resolve-PythonCommand {
  param([string]$ConfiguredPythonCommand = "")

  if ($ConfiguredPythonCommand) {
    if (-not (Get-Command $ConfiguredPythonCommand -ErrorAction SilentlyContinue)) {
      throw "Configured PythonCommand not found: $ConfiguredPythonCommand"
    }
    return $ConfiguredPythonCommand
  }

  foreach ($candidate in @("py", "python", "python3")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
      return $candidate
    }
  }

  throw "Python runtime not found. Install Python 3.12+ or pass -PythonCommand."
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
$pythonCmd = Resolve-PythonCommand -ConfiguredPythonCommand $PythonCommand
$deployScript = Join-Path $ProjectRoot "ops\winserver\deploy_winserver.ps1"
Ensure-PathExists -Path $deployScript -Label "deploy_winserver.ps1"

$frontendDist = if ($PrebuiltFrontendDist) { $PrebuiltFrontendDist } else { Join-Path $ProjectRoot "frontend\dist" }
$resolvedWheelhouse = $WheelhouseDir
if (-not $resolvedWheelhouse) {
  $candidate1 = Join-Path $ProjectRoot "ops\winserver\python_wheels"
  $candidate2 = Join-Path $ProjectRoot "python_wheels"
  if (Test-Path $candidate1) {
    $resolvedWheelhouse = $candidate1
  }
  elseif (Test-Path $candidate2) {
    $resolvedWheelhouse = $candidate2
  }
}

$deployParams = @{
  ProjectRoot = $ProjectRoot
  PythonCommand = $pythonCmd
  PythonVersion = $PythonVersion
  DatabaseUrl = $DatabaseUrl
  BackendPort = $BackendPort
  FrontendPort = $FrontendPort
  InitDatabase = $InitDatabase
  SeedData = $SeedData
  InstallServices = $InstallServices
  OpenFirewall = $OpenFirewall
}

# Prefer offline wheel install when wheelhouse is present.
if ($resolvedWheelhouse) {
  if (-not (Test-Path $resolvedWheelhouse)) {
    throw "WheelhouseDir not found: $resolvedWheelhouse"
  }
  $deployParams["WheelhouseDir"] = $resolvedWheelhouse
}

# If dist already exists in copied project, skip npm build.
if (Test-Path (Join-Path $frontendDist "index.html")) {
  $deployParams["PrebuiltFrontendDist"] = $frontendDist
}

if ($SeedData -and $SeedDataDir) {
  $deployParams["SeedDataDir"] = $SeedDataDir
}

Write-Host "[INFO] PythonCommand: $pythonCmd"
Write-Host "[INFO] ProjectRoot   : $ProjectRoot"
& $deployScript @deployParams
