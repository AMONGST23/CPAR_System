from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.urls import reverse
from django.test import TestCase
from openpyxl import load_workbook
from io import BytesIO

from surveys.models import MaternalRecord
from .models import AgentProfile


class AgentProfileSignalTests(TestCase):
    def test_profile_created_with_user(self):
        user = User.objects.create_user(username='agent1', password='secret123')
        self.assertTrue(AgentProfile.objects.filter(user=user).exists())


class AdminPanelTests(TestCase):
    def setUp(self):
        self.staff_user = get_user_model().objects.create_user(
            username='admin1',
            password='secret123',
            is_staff=True,
        )
        self.agent_user = get_user_model().objects.create_user(
            username='agent1',
            password='secret123',
        )

    def test_staff_user_can_open_admin_panel(self):
        self.client.login(username='admin1', password='secret123')
        response = self.client.get(reverse('admin_panel'))
        self.assertEqual(response.status_code, 200)

    def test_staff_user_can_create_agent(self):
        self.client.login(username='admin1', password='secret123')
        response = self.client.post(reverse('admin_panel'), {
            'action': 'create_agent',
            'create-username': 'agent2',
            'create-first_name': 'Jane',
            'create-last_name': 'Doe',
            'create-assigned_area': 'Ward 1',
            'create-phone_number': '0700000000',
            'create-password1': 'secret12345',
            'create-password2': 'secret12345',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(get_user_model().objects.filter(username='agent2').exists())

    def test_admin_can_export_records_to_excel(self):
        MaternalRecord.objects.create(
            last_name='Doe',
            first_name='Jane',
            date_collected='2026-03-24',
            address_barangay='Nairobi',
            is_currently_pregnant=True,
            ultrasound_before_24_weeks=True,
            agent=self.agent_user,
        )

        self.client.login(username='admin1', password='secret123')
        response = self.client.get(reverse('admin_export_records'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

        workbook = load_workbook(BytesIO(response.content))
        worksheet = workbook.active
        headers = [cell.value for cell in worksheet[1]]
        self.assertIn('Region', headers)
        self.assertIn('Ultrasound Before 24 Weeks', headers)

        first_row = [cell.value for cell in worksheet[2]]
        self.assertIn('Doe', first_row)
        self.assertIn('Nairobi', first_row)
        self.assertIn('Yes', first_row)

    def test_non_admin_cannot_export_records_to_excel(self):
        self.client.login(username='agent1', password='secret123')
        response = self.client.get(reverse('admin_export_records'))
        self.assertEqual(response.status_code, 302)
