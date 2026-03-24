from django.core.management.base import BaseCommand

from surveys.utils import SyncConfigurationError, sync_unsynced_records


class Command(BaseCommand):
    help = 'Confirm that pending records are marked as saved on the local server.'

    def handle(self, *args, **options):
        try:
            result = sync_unsynced_records()
        except SyncConfigurationError as error:
            self.stderr.write(self.style.ERROR(str(error)))
            return

        if result['status'] == 'error':
            self.stderr.write(self.style.ERROR(result['message']))
            return

        if result['status'] == 'partial':
            self.stdout.write(self.style.WARNING(result['message']))
            return

        self.stdout.write(self.style.SUCCESS(result['message']))
