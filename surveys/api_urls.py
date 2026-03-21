from django.urls import path
from . import api_views

urlpatterns = [
    path('sync/', api_views.SyncReceiveView.as_view(), name='api_sync'),
    path('records/', api_views.RecordListAPIView.as_view(), name='api_records'),
]
