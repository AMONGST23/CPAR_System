from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.AgentLoginView.as_view(), name='login'),
    path('logout/', views.AgentLogoutView.as_view(), name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('admin-panel/', views.admin_panel_view, name='admin_panel'),
    path('admin-panel/export-records/', views.admin_export_records_view, name='admin_export_records'),
]
