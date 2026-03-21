# CPAR Maternal Health System

Offline-aware Django web app for maternal data collection on a local network, with later sync to a remote server.

## Current Scope

- Tablet-friendly local data entry
- User authentication for agents
- Local draft protection in the browser
- Local storage in SQLite for field deployment
- Manual sync to a remote server
- Sync attempt logging
- Field encryption at rest for key personal identifiers when `FIELD_ENCRYPTION_KEY` is set

## Local Run

From `G:\CPAR_System`:

```powershell
.\venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Or use:

```powershell
.\start_local.ps1
```

Open on the host machine:

```text
http://127.0.0.1:8000
```

Open from tablets on the same Wi-Fi:

```text
http://<host-ip>:8000
```

## Environment Variables

The project reads these from the machine environment:

- `DJANGO_SECRET_KEY`
- `DJANGO_TIME_ZONE`
- `REMOTE_SYNC_URL`
- `REMOTE_SYNC_TOKEN`
- `FIELD_ENCRYPTION_KEY`

For local field deployment, `.\start_local.ps1` also loads values from:

- `.env.local.ps1`

Production-only:

- `ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`
- `CSRF_TRUSTED_ORIGINS`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `SECURE_SSL_REDIRECT`

## Encryption

If `FIELD_ENCRYPTION_KEY` is present, these values are stored encrypted at rest:

- last name
- first name
- middle name
- barangay
- municipality
- province
- contact number

Existing records created before the key was configured remain plaintext until they are edited and saved again.

## Verification Commands

Run tests:

```powershell
python manage.py test
```

Check runtime/system status:

```powershell
python manage.py system_status
```

Trigger manual sync from CLI:

```powershell
python manage.py sync_data
```

## Deployment Notes

Recommended local field setup:

1. Use one laptop as the local server.
2. Connect tablets to the same hotspot or router.
3. Start Django with `0.0.0.0:8000`.
4. Create agent accounts in Django admin.
5. Confirm access from one tablet before field use.
6. Run `python manage.py system_status` before leaving site.

## Data Backup

For the local SQLite deployment, back up:

- `db.sqlite3`
- the project folder if you want templates/static changes preserved

Quick backup example:

```powershell
Copy-Item .\db.sqlite3 ".\backup\db-$(Get-Date -Format 'yyyyMMdd-HHmmss').sqlite3"
```

## Handoff Checklist

- Migrations applied
- Superuser created
- Agent accounts created
- `FIELD_ENCRYPTION_KEY` configured
- Remote sync URL/token configured if cloud sync is required
- One local login tested
- One tablet login tested
- One record create/edit tested
- One sync attempt tested
