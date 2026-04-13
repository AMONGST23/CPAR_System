# CPAR Field Deployment Guide

## Purpose

This guide is for setting up the CPAR system on one Windows laptop that will act as the local server in a temporary clinical facility.

## What You Need

- One Windows laptop
- A Python installer file placed with the deployment package
- The CPAR project folder
- Tablets or phones connected to the same Wi-Fi or hotspot as the laptop

Recommended Python installer:

- Python 3.13 x64 from python.org
- filename example: `python-3.13.3-amd64.exe`

Place the installer in one of these folders:

- the project root folder
- `bundle\`
- `installers\`

For fully offline installation, also place the Python package bundle in:

- `bundle\wheels\`

## One-Time Setup

1. Copy the entire project folder to the laptop.
2. Double-click:

```text
install.bat
```

This script will:

- check for Python 3.13 or later
- open the bundled Python installer automatically if Python is missing
- install Python packages from `bundle\wheels\` if that offline package bundle is present
- rebuild the virtual environment if the copied folder contains one from another machine
- create the Python virtual environment
- install the project requirements
- apply database migrations

## Daily Startup

1. Double-click:

```text
start_local.bat
```

2. Keep that PowerShell window open while the system is in use.
3. On the laptop, open:

```text
http://127.0.0.1:8000
```

4. On tablets, open the network address shown in the PowerShell window, for example:

```text
http://192.168.1.10:8000
```

## Daily Shutdown

1. Return to the PowerShell window running the server.
2. Press `Ctrl+C`.
3. Double-click:

```text
backup_db.bat
```

## Backup Location

Backups are stored in:

```text
backup\
```

Each backup file includes the date and time in its filename.

## Important Notes

- The laptop must stay on while tablets are using the system.
- The PowerShell window running `start_local.ps1` must remain open.
- All devices must be on the same Wi-Fi or hotspot.
- If Windows Firewall asks for permission, allow access on the local/private network.
- If the site has no internet, make sure `bundle\wheels\` was prepared before travel.
- Do not rely on copying a `venv` from another machine. `install.bat` should build the environment on the target laptop.

## If the System Does Not Start

Double-click:

```text
install.bat
```

again, then retry:

```text
start_local.bat
```

## If Tablets Cannot Connect

- confirm the laptop and tablets are on the same network
- confirm the address entered on the tablet matches the one shown by `start_local.ps1`
- confirm the PowerShell window on the laptop is still running
- confirm Windows Firewall allowed local/private network access

## Changing Where the Installer Is Stored

If you later want the script to look somewhere else for the bundled Python installer, open:

- [install.ps1](/G:/CPAR_System/install.ps1)

At the top of the file, edit this variable:

```powershell
$BundledInstallerSearchRoots = @(
    $projectRoot,
    (Join-Path $projectRoot 'bundle'),
    (Join-Path $projectRoot 'installers')
)
```

You can add another folder, for example a flash drive:

```powershell
$BundledInstallerSearchRoots = @(
    $projectRoot,
    (Join-Path $projectRoot 'bundle'),
    'E:\CPAR_Deployment'
)
```

The script will look in those folders for a file like `python-3.13.x-amd64.exe`.

## Preparing the Offline Package Bundle

Before going to a site with limited or no internet, prepare the Python package bundle on a machine that has internet access.

From the project folder, run:

```powershell
mkdir .\bundle\wheels
python -m pip download -r requirements.txt -d .\bundle\wheels
```

This downloads the required Python packages into `bundle\wheels\`.

After that, copy the whole project folder to the flash drive. At the deployment site, `install.bat` will install packages from that local bundle without internet access.
