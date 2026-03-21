$ErrorActionPreference = 'Stop'

if (-not (Test-Path ".\venv\Scripts\Activate.ps1")) {
    Write-Error "Virtual environment not found at .\venv"
}

if (Test-Path ".\.env.local.ps1") {
    . .\.env.local.ps1
}

. .\venv\Scripts\Activate.ps1

if (-not $env:DJANGO_SETTINGS_MODULE) {
    $env:DJANGO_SETTINGS_MODULE = "cpar.settings.local"
}

Write-Host "Using settings: $env:DJANGO_SETTINGS_MODULE"
Write-Host "FIELD_ENCRYPTION_KEY configured: " -NoNewline
if ($env:FIELD_ENCRYPTION_KEY) {
    Write-Host "yes"
} else {
    Write-Host "no"
}

python manage.py runserver 0.0.0.0:8000
