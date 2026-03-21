from django.contrib import admin

from .models import MaternalRecord, SyncLog


@admin.register(MaternalRecord)
class MaternalRecordAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'age', 'address_barangay', 'date_collected', 'agent', 'is_synced']
    list_filter = ['is_synced', 'date_collected', 'agent', 'civil_status']
    search_fields = ['last_name', 'first_name', 'address_barangay', 'contact_number']
    readonly_fields = ['sync_uuid', 'created_at', 'updated_at']
    date_hierarchy = 'date_collected'
    list_select_related = ['agent']


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ['started_at', 'status', 'records_attempted', 'records_synced', 'records_failed']
    list_filter = ['status', 'started_at']
    readonly_fields = ['started_at', 'finished_at']
