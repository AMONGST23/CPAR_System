$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

# Bundled installer search locations.
# Edit this list later if you want the script to look somewhere else,
# such as a flash drive folder like 'E:\CPAR_Deployment'.
$BundledInstallerSearchRoots = @(
    $projectRoot,
    (Join-Path $projectRoot 'bundle'),
    (Join-Path $projectRoot 'installers')
)

function Get-BundledPythonInstaller {
    param (
        [string[]]$SearchRoots
    )

    foreach ($root in $SearchRoots | Where-Object { $_ -and (Test-Path $_) }) {
        try {
            $installer = Get-ChildItem $root -Filter 'python*.exe' -File -ErrorAction SilentlyContinue |
                Sort-Object Name -Descending |
                Select-Object -First 1
            if ($installer) {
                return $installer.FullName
            }
        } catch {
        }
    }

    return $null
}

function Get-PreferredPythonPath {
    $candidates = @()

    $commandPython = Get-Command python -ErrorAction SilentlyContinue
    if ($commandPython -and $commandPython.Source) {
        $candidates += $commandPython.Source
    }

    $localAppData = [Environment]::GetFolderPath('LocalApplicationData')
    $programFiles = [Environment]::GetFolderPath('ProgramFiles')
    $programFilesX86 = ${env:ProgramFiles(x86)}

    $searchRoots = @(
        (Join-Path $localAppData 'Programs\Python'),
        (Join-Path $localAppData 'Python'),
        $programFiles,
        $programFilesX86
    ) | Where-Object { $_ -and (Test-Path $_) }

    foreach ($root in $searchRoots) {
        try {
            $found = Get-ChildItem $root -Recurse -Filter python.exe -ErrorAction SilentlyContinue |
                Where-Object {
                    $_.FullName -notmatch 'WindowsApps' -and
                    $_.FullName -notmatch 'CodeBlocks\\MinGW'
                } |
                Select-Object -ExpandProperty FullName
            if ($found) {
                $candidates += $found
            }
        } catch {
        }
    }

    $uniqueCandidates = $candidates | Where-Object { $_ } | Select-Object -Unique
    foreach ($candidate in $uniqueCandidates) {
        try {
            $versionOutput = & $candidate --version 2>&1
            if ($LASTEXITCODE -eq 0 -and $versionOutput -match '^Python 3\.(1[3-9]|[2-9][0-9])') {
                return @{
                    Path = $candidate
                    Version = $versionOutput
                }
            }
        } catch {
        }
    }

    return $null
}

function Test-VenvMatchesPython {
    param (
        [string]$ProjectRoot,
        [string]$ExpectedPythonPath
    )

    $venvPython = Join-Path $ProjectRoot 'venv\Scripts\python.exe'
    $pyvenvConfig = Join-Path $ProjectRoot 'venv\pyvenv.cfg'

    if (-not (Test-Path $venvPython) -or -not (Test-Path $pyvenvConfig)) {
        return $false
    }

    $configText = Get-Content $pyvenvConfig -Raw
    if (-not $configText) {
        return $false
    }

    if ($configText -match '(?m)^executable\s*=\s*(.+)$') {
        $configuredExecutable = $Matches[1].Trim()
        try {
            $resolvedExpected = [System.IO.Path]::GetFullPath($ExpectedPythonPath)
            $resolvedConfigured = [System.IO.Path]::GetFullPath($configuredExecutable)
            return $resolvedExpected -eq $resolvedConfigured
        } catch {
            return $false
        }
    }

    return $false
}

$pythonInfo = Get-PreferredPythonPath
if (-not $pythonInfo) {
    $bundledInstaller = Get-BundledPythonInstaller -SearchRoots $BundledInstallerSearchRoots

    Write-Host ''
    Write-Host 'A usable Python 3.13+ installation was not found.' -ForegroundColor Red
    if ($bundledInstaller) {
        Write-Host "Bundled Python installer found: $bundledInstaller" -ForegroundColor Yellow
        Write-Host 'Opening the installer now. Finish the Python installation, then run install.bat again.' -ForegroundColor Yellow
        Start-Process -FilePath $bundledInstaller
    } else {
        Write-Host 'No bundled Python installer was found in the configured search folders.' -ForegroundColor Yellow
        Write-Host 'Configured bundled-installer search folders:' -ForegroundColor Yellow
        foreach ($root in $BundledInstallerSearchRoots) {
            Write-Host "  $root"
        }
        Write-Host 'Place the Python installer in one of those folders, then run install.bat again.' -ForegroundColor Yellow
    }
    Write-Host 'Do not use the Windows Store alias or Python 2 from CodeBlocks.' -ForegroundColor Yellow
    exit 1
}

$pythonPath = $pythonInfo.Path
$pythonVersion = $pythonInfo.Version
Write-Host ''
Write-Host "Using $pythonVersion" -ForegroundColor Cyan
Write-Host "Python path: $pythonPath"

$venvRoot = Join-Path $projectRoot 'venv'
$venvPython = Join-Path $projectRoot 'venv\Scripts\python.exe'
$envFile = Join-Path $projectRoot '.env.local.ps1'
$wheelhousePath = Join-Path $projectRoot 'bundle\wheels'

if (Test-Path $venvPython) {
    if (-not (Test-VenvMatchesPython -ProjectRoot $projectRoot -ExpectedPythonPath $pythonPath)) {
        Write-Host ''
        Write-Host 'Existing virtual environment belongs to another machine or Python installation.' -ForegroundColor Yellow
        Write-Host 'Rebuilding the virtual environment for this machine...' -ForegroundColor Yellow
        Remove-Item $venvRoot -Recurse -Force
    }
}

if (-not (Test-Path $venvPython)) {
    Write-Host 'Creating virtual environment...' -ForegroundColor Cyan
    & $pythonPath -m venv .\venv
}

Write-Host 'Upgrading pip...' -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip

if (Test-Path $wheelhousePath) {
    Write-Host 'Offline package bundle found. Installing project requirements from bundle\wheels...' -ForegroundColor Cyan
    & $venvPython -m pip install --no-index --find-links $wheelhousePath -r .\requirements.txt
} else {
    Write-Host 'Offline package bundle not found. Installing project requirements from the internet...' -ForegroundColor Yellow
    & $venvPython -m pip install -r .\requirements.txt
}

if (Test-Path $envFile) {
    . $envFile
} else {
    Write-Host ''
    Write-Host 'Warning: .env.local.ps1 was not found.' -ForegroundColor Yellow
    Write-Host 'The system will still run, but encryption at rest will not be configured until the file is added.' -ForegroundColor Yellow
}

if (-not $env:DJANGO_SETTINGS_MODULE) {
    $env:DJANGO_SETTINGS_MODULE = 'cpar.settings.local'
}

Write-Host 'Applying database migrations...' -ForegroundColor Cyan
& $venvPython manage.py migrate

Write-Host ''
Write-Host 'Installation complete.' -ForegroundColor Green
Write-Host 'Next steps:' -ForegroundColor Cyan
Write-Host '  1. Run start_local.ps1 to start the system'
Write-Host '  2. Open http://127.0.0.1:8000 on this laptop'
Write-Host '  3. Use backup_db.ps1 at the end of the day to back up records'
Write-Host ''
