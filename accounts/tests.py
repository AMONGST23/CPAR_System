from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.urls import reverse
from django.test import TestCase

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
