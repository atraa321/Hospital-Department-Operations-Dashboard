param(
  [string]$MysqlBin = "C:\Program Files\MySQL\MySQL Server 8.0\bin",
  [string]$User = "root",
  [string]$Password = "123456",
  [string]$Database = "disease_analytics",
  [string]$BackupDir = "D:\backup\disease-analytics"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupDir)) {
  New-Item -Path $BackupDir -ItemType Directory | Out-Null
}

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$file = Join-Path $BackupDir "$Database`_$ts.sql"

& "$MysqlBin\mysqldump.exe" -u$User -p$Password --single-transaction --routines --events $Database > $file
Write-Host "Backup completed: $file"
