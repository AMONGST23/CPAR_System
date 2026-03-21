from django.contrib.auth.models import User
from django.db import models


class AgentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, blank=True)
    assigned_area = models.CharField(
        max_length=255,
        blank=True,
        help_text='Barangay/municipality assigned to this agent',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        area = f" - {self.assigned_area}" if self.assigned_area else ""
        return f"{self.user.get_full_name() or self.user.username}{area}"
