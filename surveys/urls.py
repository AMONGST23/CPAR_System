from django.urls import path
from . import views

urlpatterns = [
    path('', views.record_list, name='record_list'),
    path('new/', views.record_create, name='record_create'),
    path('<int:pk>/', views.record_detail, name='record_detail'),
    path('<int:pk>/edit/', views.record_edit, name='record_edit'),
    path('<int:pk>/delete/', views.record_delete, name='record_delete'),
    path('sync/', views.trigger_sync, name='trigger_sync'),
]
