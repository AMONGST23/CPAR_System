import datetime
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from .crypto import decrypt_value, encrypt_value
from .forms import MaternalRecordForm
from .models import MaternalRecord, SyncLog
from .utils import sync_unsynced_records


class MaternalRecordFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='agent1', password='secret123')

    def test_form_accepts_minimum_required_fields(self):
        form = MaternalRecordForm(
            data={
                'last_name': 'Doe',
                'first_name': 'Jane',
                'date_collected': '2026-03-20',
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

        record = form.save(commit=False)
        record.agent = self.user
        record.save()

        self.assertEqual(MaternalRecord.objects.count(), 1)

    def test_para_cannot_exceed_gravida(self):
        form = MaternalRecordForm(
            data={
                'last_name': 'Doe',
                'first_name': 'Jane',
                'date_collected': '2026-03-20',
                'gravida': 1,
                'para': 2,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn('para', form.errors)

    def test_current_pregnancy_requires_lmp_or_edd(self):
        form = MaternalRecordForm(
            data={
                'last_name': 'Doe',
                'first_name': 'Jane',
                'date_collected': '2026-03-20',
                'is_currently_pregnant': 'on',
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn('lmp', form.errors)


class MaternalRecordModelTests(TestCase):
    def test_full_name_formats_middle_initial(self):
        record = MaternalRecord(
            last_name='Doe',
            first_name='Jane',
            middle_name='Ann',
            date_collected=datetime.date(2026, 3, 20),
        )
        self.assertEqual(record.full_name, 'Doe, Jane A.')


class SyncWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='agent2', password='secret123')

    @patch('surveys.utils.settings.REMOTE_SYNC_URL', 'https://example.com/api/sync/')
    @patch('surveys.utils.settings.REMOTE_SYNC_TOKEN', 'token-123')
    @patch('surveys.utils.urllib.request.urlopen')
    def test_sync_marks_only_returned_records_as_synced(self, mock_urlopen):
        first = MaternalRecord.objects.create(
            last_name='One',
            first_name='Jane',
            date_collected='2026-03-20',
            agent=self.user,
        )
        second = MaternalRecord.objects.create(
            last_name='Two',
            first_name='Janet',
            date_collected='2026-03-20',
            agent=self.user,
        )

        response = mock_urlopen.return_value.__enter__.return_value
        response.read.return_value = (
            '{"sync_uuids": ["%s"], "errors": [{"sync_uuid": "%s", "errors": {"field": ["bad"]}}]}'
            % (first.sync_uuid, second.sync_uuid)
        ).encode()

        result = sync_unsynced_records()

        first.refresh_from_db()
        second.refresh_from_db()

        self.assertEqual(result['status'], 'partial')
        self.assertTrue(first.is_synced)
        self.assertFalse(second.is_synced)
        self.assertEqual(SyncLog.objects.count(), 1)


class EncryptionTests(TestCase):
    TEST_KEY = 'PXB8tRY0RpI53M1jhyfi4VEq2q4mVe5Q6OM5P4F7X5A='

    @override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
    def test_sensitive_fields_are_encrypted_at_rest(self):
        user = User.objects.create_user(username='agent3', password='secret123')
        record = MaternalRecord.objects.create(
            last_name='Doe',
            first_name='Jane',
            contact_number='0712345678',
            date_collected='2026-03-20',
            agent=user,
        )

        raw = MaternalRecord.objects.values('last_name', 'first_name', 'contact_number').get(pk=record.pk)
        self.assertNotEqual(raw['last_name'], 'Doe')
        self.assertTrue(raw['last_name'].startswith('enc::'))
        self.assertEqual(MaternalRecord.objects.get(pk=record.pk).last_name, 'Doe')

    @override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
    def test_encrypt_and_decrypt_helpers_round_trip(self):
        encrypted = encrypt_value('secret')
        self.assertNotEqual(encrypted, 'secret')
        self.assertEqual(decrypt_value(encrypted), 'secret')
