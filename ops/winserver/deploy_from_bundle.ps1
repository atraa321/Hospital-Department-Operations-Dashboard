param(
  [Parameter(Mandatory = $true)][string]$BundleDir,
  [string]$ProjectRoot = "D:\病种分析V2",
  [string]$DatabaseUrl = "",
  [int]$BackendPort = 18080,
  [int]$FrontendPort = 5173,
  [string]$CorsOriginsJson = "",
  [bool]$InstallServices = $true,
  [bool]$OpenFirewall = $true
)

$ErrorActionPreference = "Stop"

$wheelhouse = Join-Path $BundleDir "python_wheels"
$frontendDist = Join-Path $BundleDir "frontend_dist"
$deployScript = Join-Path $ProjectRoot "ops\winserver\deploy_winserver.ps1"

if (-not (Test-Path $BundleDir)) {
  throw "BundleDir not found: $BundleDir"
}
if (-not (Test-Path $wheelhouse)) {
  throw "python_wheels not found: $wheelhouse"
}
if (-not (Test-Path (Join-Path $frontendDist "index.html"))) {
  throw "frontend_dist/index.html not found: $frontendDist"
}
if (-not (Test-Path $deployScript)) {
  throw "deploy script not found: $deployScript"
}

& $deployScript `
  -ProjectRoot $ProjectRoot `
  -WheelhouseDir $wheelhouse `
  -PrebuiltFrontendDist $frontendDist `
  -DatabaseUrl $DatabaseUrl `
  -BackendPort $BackendPort `
  -FrontendPort $FrontendPort `
  -CorsOriginsJson $CorsOriginsJson `
  -InstallServices:$InstallServices `
  -OpenFirewall:$OpenFirewall
