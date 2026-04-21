from rest_framework import serializers
from .models import MaternalRecord


class MaternalRecordSerializer(serializers.ModelSerializer):
    agent_username = serializers.CharField(source='agent.username', read_only=True)
    sync_uuid = serializers.UUIDField(required=True)

    class Meta:
        model = MaternalRecord
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        """On remote server: use sync_uuid to prevent duplicates."""
        instance, _ = MaternalRecord.objects.update_or_create(
            sync_uuid=validated_data['sync_uuid'],
            defaults={**validated_data, 'is_synced': True},
        )
        return instance
