param(
  [string]$MysqlBin = "C:\Program Files\MySQL\MySQL Server 8.0\bin",
  [string]$User = "root",
  [string]$Password = "123456",
  [string]$Database = "disease_analytics",
  [Parameter(Mandatory = $true)][string]$SqlFile
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $SqlFile)) {
  throw "SQL file not found: $SqlFile"
}

& "$MysqlBin\mysql.exe" -u$User -p$Password $Database < $SqlFile
Write-Host "Restore completed from: $SqlFile"
