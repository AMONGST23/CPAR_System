$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$venvPython = Join-Path $projectRoot 'venv\Scripts\python.exe'
$pyvenvConfig = Join-Path $projectRoot 'venv\pyvenv.cfg'
$envFile = Join-Path $projectRoot '.env.local.ps1'

function Test-LocalVenvUsable {
    param (
        [string]$PythonPath,
        [string]$ConfigPath
    )

    if (-not (Test-Path $PythonPath) -or -not (Test-Path $ConfigPath)) {
        return $false
    }

    try {
        $null = & $PythonPath --version 2>$null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

if (-not (Test-LocalVenvUsable -PythonPath $venvPython -ConfigPath $pyvenvConfig)) {
    Write-Host ''
    Write-Host 'The local virtual environment is missing or invalid for this machine.' -ForegroundColor Red
    Write-Host 'Run install.bat first to rebuild the environment on this laptop.' -ForegroundColor Yellow
    exit 1
}

if (Test-Path $envFile) {
    . $envFile
}

if (-not $env:DJANGO_SETTINGS_MODULE) {
    $env:DJANGO_SETTINGS_MODULE = 'cpar.settings.local'
}

$hostAddresses = @('127.0.0.1')
try {
    $ipv4 = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
        Where-Object {
            $_.IPAddress -notlike '127.*' -and
            $_.IPAddress -notlike '169.254.*'
        } |
        Select-Object -ExpandProperty IPAddress -Unique

    if ($ipv4) {
        $hostAddresses += $ipv4
    }
} catch {
}

Write-Host ''
Write-Host 'CPAR local server starting...' -ForegroundColor Cyan
Write-Host "Settings: $env:DJANGO_SETTINGS_MODULE"
Write-Host 'Encryption key configured: ' -NoNewline
if ($env:FIELD_ENCRYPTION_KEY) {
    Write-Host 'yes' -ForegroundColor Green
} else {
    Write-Host 'no' -ForegroundColor Yellow
}
Write-Host ''
Write-Host 'Open on this laptop:' -ForegroundColor Cyan
Write-Host '  http://127.0.0.1:8000'
Write-Host ''
Write-Host 'Open on tablets on the same network:' -ForegroundColor Cyan
foreach ($ip in $hostAddresses | Select-Object -Unique) {
    Write-Host "  http://$ip`:8000"
}
Write-Host ''
Write-Host 'Press Ctrl+C to stop the server.' -ForegroundColor Yellow
Write-Host ''

& $venvPython manage.py runserver 0.0.0.0:8000
