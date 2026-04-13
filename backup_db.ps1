$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$databasePath = Join-Path $projectRoot 'db.sqlite3'
$backupDir = Join-Path $projectRoot 'backup'

if (-not (Test-Path $databasePath)) {
    Write-Host 'Database file db.sqlite3 was not found.' -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir | Out-Null
}

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupPath = Join-Path $backupDir "db-$timestamp.sqlite3"

Copy-Item $databasePath $backupPath

Write-Host ''
Write-Host 'Backup created successfully:' -ForegroundColor Green
Write-Host "  $backupPath"
Write-Host ''
