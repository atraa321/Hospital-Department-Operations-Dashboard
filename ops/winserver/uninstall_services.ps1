param(
  [string]$BackendServiceName = "DiseaseAnalyticsBackend",
  [string]$FrontendServiceName = "DiseaseAnalyticsFrontend"
)

$ErrorActionPreference = "Stop"

function Test-Admin {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($identity)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Remove-ServiceIfExists {
  param([Parameter(Mandatory = $true)][string]$Name)

  $svc = Get-Service -Name $Name -ErrorAction SilentlyContinue
  if (-not $svc) {
    Write-Host "[INFO] service not found: $Name"
    return
  }

  if ($svc.Status -ne "Stopped") {
    sc.exe stop $Name | Out-Null
    Start-Sleep -Seconds 2
  }
  sc.exe delete $Name | Out-Null
  Write-Host "[OK] service removed: $Name"
}

if (-not (Test-Admin)) {
  throw "请使用管理员权限运行本脚本。"
}

Remove-ServiceIfExists -Name $FrontendServiceName
Remove-ServiceIfExists -Name $BackendServiceName
