from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AgentProfile


@receiver(post_save, sender=User)
def ensure_agent_profile(sender, instance, created, **kwargs):
    if created:
        AgentProfile.objects.create(user=instance)
        return

    AgentProfile.objects.get_or_create(user=instance)
