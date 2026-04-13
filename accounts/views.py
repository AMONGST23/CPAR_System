from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from openpyxl import Workbook

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


def _filter_records(query, agent_id=None):
    records = list(MaternalRecord.objects.select_related('agent').all())

    if agent_id:
        records = [
            record for record in records
            if record.agent and str(record.agent_id) == str(agent_id)
        ]

    if not query:
        return records

    q = query.strip().lower()
    return [
        record for record in records
        if q in (record.last_name or '').lower()
        or q in (record.first_name or '').lower()
        or q in (record.address_barangay or '').lower()
    ]


def _format_export_value(record, field_name):
    value = getattr(record, field_name)
    if field_name == 'agent':
        return record.agent.username if record.agent else ''
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'Yes' if value else 'No'

    display_method = getattr(record, f'get_{field_name}_display', None)
    if callable(display_method):
        return display_method()

    return str(value)


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

    users = User.objects.select_related('profile').order_by('username')
    selected_agent_id = request.GET.get('agent', '').strip()
    q = request.GET.get('q', '')
    records = _filter_records(q, agent_id=selected_agent_id)
    sync_logs = SyncLog.objects.all()[:10]
    agent_summaries = []
    for listed_user in users:
        record_count = MaternalRecord.objects.filter(agent=listed_user).count()
        if record_count == 0 and not listed_user.is_staff:
            continue
        agent_summaries.append({
            'user': listed_user,
            'record_count': record_count,
        })

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
        'agent_summaries': agent_summaries,
        'summary': summary,
        'q': request.GET.get('q', ''),
        'selected_agent_id': selected_agent_id,
    })


@user_passes_test(_is_admin_user)
def admin_export_records_view(request):
    q = request.GET.get('q', '')
    selected_agent_id = request.GET.get('agent', '').strip()
    records = _filter_records(q, agent_id=selected_agent_id)

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = 'Maternal Records'

    fields = [
        ('sync_uuid', 'Sync UUID'),
        ('is_synced', 'Synced'),
        ('agent', 'Agent Username'),
        ('date_collected', 'Date Collected'),
        ('last_name', 'Last Name'),
        ('first_name', 'First Name'),
        ('middle_name', 'Middle Name'),
        ('age', 'Age'),
        ('civil_status', 'Marital Status'),
        ('address_barangay', 'Region'),
        ('address_municipality', 'District'),
        ('address_province', 'Village'),
        ('contact_number', 'Contact Number'),
        ('educational_attainment', 'Educational Attainment'),
        ('gravida', 'Gravida'),
        ('para', 'Para'),
        ('abortion', 'Abortion'),
        ('living_children', 'Living Children'),
        ('last_delivery_date', 'Last Delivery Date'),
        ('last_delivery_type', 'Last Delivery Type'),
        ('is_currently_pregnant', 'Currently Pregnant'),
        ('lmp', 'LMP'),
        ('age_of_gestation_weeks', 'Age of Gestation (Weeks)'),
        ('expected_date_of_delivery', 'Expected Date of Delivery'),
        ('prenatal_visit_count', 'Prenatal Visit Count'),
        ('prenatal_facility', 'Prenatal Facility'),
        ('weight_kg', 'Weight (kg)'),
        ('height_cm', 'Height (cm)'),
        ('blood_pressure', 'Blood Pressure'),
        ('hemoglobin_level', 'Hemoglobin Level'),
        ('nutritional_status', 'Nutritional Status'),
        ('tetanus_toxoid_status', 'Tetanus Toxoid Status'),
        ('iron_supplementation', 'Iron Supplementation'),
        ('vitamin_a_supplementation', 'Vitamin A Supplementation'),
        ('dental_checkup', 'Dental Check-up'),
        ('family_planning_counseling', 'Family Planning Counseling'),
        ('first_ultrasound_current_pregnancy', 'First Ultrasound This Pregnancy'),
        ('previous_pregnancies_with_ultrasound', 'Previous Pregnancies Included Ultrasound'),
        ('previous_pregnancies_with_ultrasound_count', 'Number of Previous Pregnancies With Ultrasound'),
        ('ultrasound_service_helpful', 'Ultrasound Service Helpful'),
        ('benefit_saves_travel_time', 'Benefit: Saves Travel Time'),
        ('benefit_reduces_transport_costs', 'Benefit: Reduces Transport Costs'),
        ('benefit_detects_problems_early', 'Benefit: Detects Problems Early'),
        ('benefit_understands_baby_health', 'Benefit: Improves Understanding of Baby Health'),
        ('benefit_encourages_anc', 'Benefit: Encourages ANC Attendance'),
        ('benefit_enables_early_referral', 'Benefit: Enables Early Referral'),
        ('benefit_knows_due_date', 'Benefit: Helps Know Due Date'),
        ('benefit_other', 'Other Ultrasound Benefit'),
        ('ultrasound_before_24_weeks', 'Ultrasound Before 24 Weeks'),
        ('ultrasound_screened_high_risk', 'Ultrasound High-Risk Screening'),
        ('complication_placenta_previa', 'Placenta Previa Detected'),
        ('complication_multiple_gestation', 'Multiple Gestation Detected'),
        ('complication_breech', 'Breech Detected'),
        ('complication_other', 'Other Pregnancy Complications'),
        ('first_ultrasound_gestation_weeks', 'First Ultrasound Gestational Age (Weeks)'),
        ('high_risk_pregnancy', 'High-Risk Pregnancy'),
        ('high_risk_identified_through_ruaa', 'High-Risk Identified Through RUAA'),
        ('referred_high_risk_pregnancy', 'Referred High-Risk Pregnancy'),
        ('referral_completed', 'Referral Completed'),
        ('referral_received_appropriate_care', 'Appropriate Referral Care Received'),
        ('referral_reason_obstetric_complication', 'Referral Reason: Obstetric Complication'),
        ('referral_reason_no_fetal_heartbeat', 'Referral Reason: No Fetal Heartbeat'),
        ('referral_reason_malpresentation', 'Referral Reason: Malpresentation'),
        ('referral_reason_multiple_pregnancy', 'Referral Reason: Multiple Pregnancy'),
        ('referral_reason_hiv_related', 'Referral Reason: HIV-Related'),
        ('referral_reason_severe_anemia_malnutrition', 'Referral Reason: Severe Anemia/Malnutrition'),
        ('referral_reason_other', 'Referral Reason: Other'),
        ('gbv_asked_about_safety', 'GBV: Asked About Safety'),
        ('gbv_respectful_supportive_provider', 'GBV: Respectful and Supportive Provider'),
        ('gbv_given_information_for_help', 'GBV: Given Information for Help'),
        ('gbv_offered_help_or_referral', 'GBV: Offered Help or Referral'),
        ('gbv_felt_safe_discussing_issues', 'GBV: Felt Safe Discussing Issues'),
        ('nutrition_counseling_received', 'Nutrition Counseling Received'),
        ('maternal_supplements_received', 'Maternal Supplements Received'),
        ('severe_malnutrition_referred', 'Severe Malnutrition Referred'),
        ('nutrition_discussed_foods', 'Nutrition: Discussed Foods'),
        ('nutrition_advised_iron_folic', 'Nutrition: Advised Iron/Folic'),
        ('nutrition_understands_important_foods', 'Nutrition: Understands Important Foods'),
        ('nutrition_improved_diet_since_visit', 'Nutrition: Improved Diet Since Visit'),
        ('fp_discussed_options', 'FP: Discussed Options'),
        ('fp_methods_explained_clearly', 'FP: Methods Explained Clearly'),
        ('fp_understands_post_delivery_options', 'FP: Understands Options After Delivery'),
        ('fp_given_opportunity_to_ask_questions', 'FP: Opportunity to Ask Questions'),
        ('sti_discussed_infections', 'STI: Discussed Infections'),
        ('sti_asked_about_symptoms', 'STI: Asked About Symptoms'),
        ('sti_advised_on_prevention', 'STI: Advised on Prevention'),
        ('sti_offered_testing_or_treatment', 'STI: Offered Testing or Treatment'),
        ('client_treated_with_respect', 'Client Experience: Treated With Respect'),
        ('client_explanations_clear', 'Client Experience: Explanations Were Clear'),
        ('client_visit_helped_understand_health', 'Client Experience: Visit Helped Understanding'),
        ('client_most_helpful_feedback', 'Client Experience: Most Helpful Feedback'),
        ('notes', 'Notes'),
        ('created_at', 'Created At'),
        ('updated_at', 'Updated At'),
    ]

    worksheet.append([header for _, header in fields])
    for record in records:
        worksheet.append([
            _format_export_value(record, field_name)
            for field_name, _ in fields
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    timestamp = timezone.now().strftime('%Y%m%d-%H%M%S')
    response['Content-Disposition'] = f'attachment; filename="maternal-records-{timestamp}.xlsx"'
    workbook.save(response)
    return response
