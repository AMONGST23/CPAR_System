from django.utils import timezone


class SyncConfigurationError(Exception):
    pass


def sync_unsynced_records():
    from .models import MaternalRecord, SyncLog

    unsynced = MaternalRecord.objects.filter(is_synced=False).order_by('created_at')
    total_records = unsynced.count()

    if total_records == 0:
        log = SyncLog.objects.create(
            status=SyncLog.STATUS_SKIPPED,
            records_attempted=0,
            records_synced=0,
            records_failed=0,
            finished_at=timezone.now(),
            message='All records are already saved on the local server.',
        )
        return {
            'status': 'ok',
            'message': log.message,
            'attempted': 0,
            'synced': 0,
            'failed': 0,
            'errors': [],
            'log': log,
        }

    sync_log = SyncLog.objects.create(
        status=SyncLog.STATUS_RUNNING,
        records_attempted=total_records,
        message='Local save confirmation started.',
    )

    synced_count = unsynced.update(is_synced=True)
    failed_count = 0

    sync_log.records_synced = synced_count
    sync_log.records_failed = failed_count
    sync_log.finished_at = timezone.now()
    sync_log.error_details = {}
    sync_log.status = SyncLog.STATUS_SUCCESS
    sync_log.message = f'Confirmed local save for {synced_count} record(s).'

    sync_log.save()

    return {
        'status': 'ok',
        'message': sync_log.message,
        'attempted': total_records,
        'synced': synced_count,
        'failed': failed_count,
        'errors': [],
        'log': sync_log,
    }
