from django.conf import settings
from django.core.management.base import BaseCommand

from surveys.models import MaternalRecord, SyncLog


class Command(BaseCommand):
    help = 'Show runtime status for local deployment readiness.'

    def handle(self, *args, **options):
        db_engine = settings.DATABASES['default']['ENGINE']
        total_records = MaternalRecord.objects.count()
        unsynced_records = MaternalRecord.objects.filter(is_synced=False).count()
        last_sync = SyncLog.objects.first()

        self.stdout.write('CPAR system status')
        self.stdout.write(f'Database engine: {db_engine}')
        self.stdout.write('Local storage mode: yes')
        self.stdout.write(f'Encryption configured: {"yes" if getattr(settings, "FIELD_ENCRYPTION_KEY", "") else "no"}')
        self.stdout.write(f'Total records: {total_records}')
        self.stdout.write(f'Pending local confirmation: {unsynced_records}')

        if last_sync:
            self.stdout.write(
                f'Last local save check: {last_sync.get_status_display()} at {last_sync.started_at:%Y-%m-%d %H:%M}'
            )
            self.stdout.write(f'Last local save message: {last_sync.message}')
        else:
            self.stdout.write('Last local save check: none')
