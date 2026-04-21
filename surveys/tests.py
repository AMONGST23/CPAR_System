import datetime
import json
import uuid

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

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

    def test_form_accepts_nullable_client_feedback_choices(self):
        form = MaternalRecordForm(
            data={
                'last_name': 'Doe',
                'first_name': 'Jane',
                'date_collected': '2026-03-20',
                'gbv_offered_help_or_referral': '',
                'sti_offered_testing_or_treatment': 'false',
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data['gbv_offered_help_or_referral'])
        self.assertFalse(form.cleaned_data['sti_offered_testing_or_treatment'])

    def test_previous_ultrasound_count_required_when_previous_ultrasound_is_yes(self):
        form = MaternalRecordForm(
            data={
                'last_name': 'Doe',
                'first_name': 'Jane',
                'date_collected': '2026-03-20',
                'previous_pregnancies_with_ultrasound': 'on',
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn('previous_pregnancies_with_ultrasound_count', form.errors)

    def test_home_delivery_support_required_for_home_delivery_location(self):
        form = MaternalRecordForm(
            data={
                'last_name': 'Doe',
                'first_name': 'Jane',
                'date_collected': '2026-03-20',
                'last_delivery_location': 'home',
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn('home_delivery_support', form.errors)


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

    def test_sync_marks_all_pending_records_as_saved_locally(self):
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

        result = sync_unsynced_records()

        first.refresh_from_db()
        second.refresh_from_db()

        self.assertEqual(result['status'], 'ok')
        self.assertTrue(first.is_synced)
        self.assertTrue(second.is_synced)
        self.assertEqual(SyncLog.objects.count(), 1)
        self.assertEqual(result['synced'], 2)


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


class RecordSyncApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='agent-sync', password='secret123')
        self.url = reverse('record_sync_api')

    def test_authenticated_sync_creates_record_and_marks_it_synced(self):
        self.client.force_login(self.user)
        sync_uuid = str(uuid.uuid4())

        response = self.client.post(
            self.url,
            data=json.dumps({
                'sync_uuid': sync_uuid,
                'last_name': 'Doe',
                'first_name': 'Jane',
                'date_collected': '2026-04-22',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        record = MaternalRecord.objects.get(sync_uuid=sync_uuid)
        self.assertEqual(record.agent, self.user)
        self.assertTrue(record.is_synced)

    def test_sync_upserts_existing_record_using_sync_uuid(self):
        self.client.force_login(self.user)
        sync_uuid = str(uuid.uuid4())

        first_response = self.client.post(
            self.url,
            data=json.dumps({
                'sync_uuid': sync_uuid,
                'last_name': 'Doe',
                'first_name': 'Jane',
                'date_collected': '2026-04-22',
            }),
            content_type='application/json',
        )
        self.assertEqual(first_response.status_code, 201)

        second_response = self.client.post(
            self.url,
            data=json.dumps({
                'sync_uuid': sync_uuid,
                'last_name': 'Doe',
                'first_name': 'Janet',
                'date_collected': '2026-04-22',
            }),
            content_type='application/json',
        )

        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(MaternalRecord.objects.count(), 1)
        record = MaternalRecord.objects.get(sync_uuid=sync_uuid)
        self.assertEqual(record.first_name, 'Janet')

    def test_sync_api_requires_authentication(self):
        response = self.client.post(
            self.url,
            data=json.dumps({
                'sync_uuid': str(uuid.uuid4()),
                'last_name': 'Doe',
                'first_name': 'Jane',
                'date_collected': '2026-04-22',
            }),
            content_type='application/json',
        )

        self.assertIn(response.status_code, [401, 403])
