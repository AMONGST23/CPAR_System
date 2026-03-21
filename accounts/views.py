from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from surveys.models import MaternalRecord, SyncLog
from surveys.utils import SyncConfigurationError, sync_unsynced_records

from .forms import AgentCreateForm, PasswordResetForm
from .models import AgentProfile


class AgentLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True


class AgentLogoutView(LogoutView):
    next_page = '/accounts/login/'


def _is_admin_user(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


@login_required
def profile_view(request):
    profile, _ = AgentProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        profile.phone_number = request.POST.get('phone_number', '').strip()
        profile.assigned_area = request.POST.get('assigned_area', '').strip()
        profile.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('profile')
    return render(request, 'accounts/profile.html', {'profile': profile})


@user_passes_test(_is_admin_user)
def admin_panel_view(request):
    create_form = AgentCreateForm(prefix='create')
    password_form = PasswordResetForm(prefix='password')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_agent':
            create_form = AgentCreateForm(request.POST, prefix='create')
            if create_form.is_valid():
                user = create_form.save(commit=False)
                user.is_staff = False
                user.is_active = True
                user.set_password(create_form.cleaned_data['password1'])
                user.save()

                profile, _ = AgentProfile.objects.get_or_create(user=user)
                profile.assigned_area = create_form.cleaned_data.get('assigned_area', '')
                profile.phone_number = create_form.cleaned_data.get('phone_number', '')
                profile.save()

                messages.success(request, f'Agent account created for {user.username}.')
                return redirect('admin_panel')

        elif action == 'toggle_user':
            target_user = get_object_or_404(User, pk=request.POST.get('user_id'))
            if target_user == request.user:
                messages.error(request, 'You cannot disable your own account from this panel.')
            else:
                target_user.is_active = not target_user.is_active
                target_user.save(update_fields=['is_active'])
                state = 'activated' if target_user.is_active else 'disabled'
                messages.success(request, f'User {target_user.username} {state}.')
            return redirect('admin_panel')

        elif action == 'reset_password':
            password_form = PasswordResetForm(request.POST, prefix='password')
            target_user = get_object_or_404(User, pk=request.POST.get('user_id'))
            if password_form.is_valid():
                target_user.set_password(password_form.cleaned_data['new_password'])
                target_user.save()
                messages.success(request, f'Password reset for {target_user.username}.')
                return redirect('admin_panel')

        elif action == 'run_sync':
            try:
                result = sync_unsynced_records()
                level = messages.SUCCESS if result['status'] in ['ok', 'partial'] else messages.ERROR
                messages.add_message(request, level, result['message'])
            except SyncConfigurationError as error:
                messages.error(request, str(error))
            return redirect('admin_panel')

    q = request.GET.get('q', '').strip().lower()
    records = list(MaternalRecord.objects.select_related('agent').all())
    if q:
        records = [
            record for record in records
            if q in (record.last_name or '').lower()
            or q in (record.first_name or '').lower()
            or q in (record.address_barangay or '').lower()
        ]

    users = User.objects.select_related('profile').order_by('username')
    sync_logs = SyncLog.objects.all()[:10]
    summary = {
        'users': users.count(),
        'records': MaternalRecord.objects.count(),
        'unsynced': MaternalRecord.objects.filter(is_synced=False).count(),
    }

    return render(request, 'accounts/admin_panel.html', {
        'create_form': create_form,
        'password_form': password_form,
        'users': users,
        'records': records[:20],
        'sync_logs': sync_logs,
        'summary': summary,
        'q': request.GET.get('q', ''),
    })
