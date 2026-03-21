import json
import urllib.error
import urllib.request

from django.conf import settings
from django.utils import timezone

from .serializers import MaternalRecordSerializer


class SyncConfigurationError(Exception):
    pass


def sync_unsynced_records():
    from .models import MaternalRecord, SyncLog

    remote_url = getattr(settings, 'REMOTE_SYNC_URL', '')
    token = getattr(settings, 'REMOTE_SYNC_TOKEN', '')

    if not remote_url:
        raise SyncConfigurationError('Remote sync URL is not configured.')

    unsynced = MaternalRecord.objects.filter(is_synced=False).order_by('created_at')
    total_records = unsynced.count()

    if total_records == 0:
        log = SyncLog.objects.create(
            status=SyncLog.STATUS_SKIPPED,
            records_attempted=0,
            records_synced=0,
            records_failed=0,
            finished_at=timezone.now(),
            message='Nothing to sync.',
        )
        return {
            'status': 'ok',
            'message': 'Nothing to sync.',
            'attempted': 0,
            'synced': 0,
            'failed': 0,
            'errors': [],
            'log': log,
        }

    sync_log = SyncLog.objects.create(
        status=SyncLog.STATUS_RUNNING,
        records_attempted=total_records,
        message='Sync started.',
    )

    data = MaternalRecordSerializer(unsynced, many=True).data
    payload = json.dumps({'records': list(data)}).encode('utf-8')
    request = urllib.request.Request(
        remote_url,
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Token {token}',
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode() or '{}')
    except urllib.error.URLError as error:
        sync_log.status = SyncLog.STATUS_FAILED
        sync_log.records_synced = 0
        sync_log.records_failed = total_records
        sync_log.finished_at = timezone.now()
        sync_log.message = f'Network error: {error.reason}'
        sync_log.save()
        return {
            'status': 'error',
            'message': sync_log.message,
            'attempted': total_records,
            'synced': 0,
            'failed': total_records,
            'errors': [],
            'log': sync_log,
        }
    except Exception as error:
        sync_log.status = SyncLog.STATUS_FAILED
        sync_log.records_synced = 0
        sync_log.records_failed = total_records
        sync_log.finished_at = timezone.now()
        sync_log.message = f'Unexpected sync error: {error}'
        sync_log.save()
        return {
            'status': 'error',
            'message': sync_log.message,
            'attempted': total_records,
            'synced': 0,
            'failed': total_records,
            'errors': [],
            'log': sync_log,
        }

    saved_sync_uuids = body.get('sync_uuids', [])
    errors = body.get('errors', [])
    synced_count = len(saved_sync_uuids)
    failed_count = max(total_records - synced_count, 0)

    if saved_sync_uuids:
        MaternalRecord.objects.filter(sync_uuid__in=saved_sync_uuids).update(is_synced=True)

    sync_log.records_synced = synced_count
    sync_log.records_failed = failed_count
    sync_log.finished_at = timezone.now()
    sync_log.error_details = {'errors': errors}

    if failed_count:
        sync_log.status = SyncLog.STATUS_PARTIAL
        sync_log.message = f'Synced {synced_count} record(s); {failed_count} failed.'
    else:
        sync_log.status = SyncLog.STATUS_SUCCESS
        sync_log.message = f'Synced {synced_count} record(s) successfully.'

    sync_log.save()

    return {
        'status': 'ok' if failed_count == 0 else 'partial',
        'message': sync_log.message,
        'attempted': total_records,
        'synced': synced_count,
        'failed': failed_count,
        'errors': errors,
        'log': sync_log,
    }
