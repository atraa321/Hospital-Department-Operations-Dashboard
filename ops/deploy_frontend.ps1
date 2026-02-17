param(
  [string]$ProjectRoot = "D:\病种分析V2",
  [string]$DistTarget = "D:\deploy\disease-analytics-frontend"
)

$ErrorActionPreference = "Stop"

$frontendPath = Join-Path $ProjectRoot "frontend"
Set-Location $frontendPath

npm install
npm run build

if (-not (Test-Path $DistTarget)) {
  New-Item -Path $DistTarget -ItemType Directory | Out-Null
}

Copy-Item ".\dist\*" $DistTarget -Recurse -Force
Write-Host "Frontend build copied to $DistTarget"
