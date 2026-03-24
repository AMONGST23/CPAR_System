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


def _filter_records(query):
    records = list(MaternalRecord.objects.select_related('agent').all())
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

    q = request.GET.get('q', '')
    records = _filter_records(q)

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


@user_passes_test(_is_admin_user)
def admin_export_records_view(request):
    q = request.GET.get('q', '')
    records = _filter_records(q)

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
        ('date_of_birth', 'Date of Birth'),
        ('age', 'Age'),
        ('civil_status', 'Civil Status'),
        ('address_barangay', 'Region'),
        ('address_municipality', 'Municipality'),
        ('address_province', 'Province'),
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
        ('ultrasound_before_24_weeks', 'Ultrasound Before 24 Weeks'),
        ('ultrasound_screened_high_risk', 'Ultrasound High-Risk Screening'),
        ('complication_placenta_previa', 'Placenta Previa Detected'),
        ('complication_multiple_gestation', 'Multiple Gestation Detected'),
        ('complication_breech', 'Breech Detected'),
        ('complication_other', 'Other Pregnancy Complications'),
        ('first_ultrasound_gestation_weeks', 'First Ultrasound Gestational Age (Weeks)'),
        ('high_risk_identified_through_ruaa', 'High-Risk Identified Through RUAA'),
        ('referred_high_risk_pregnancy', 'Referred High-Risk Pregnancy'),
        ('referral_completed', 'Referral Completed'),
        ('referral_received_appropriate_care', 'Appropriate Referral Care Received'),
        ('nutrition_counseling_received', 'Nutrition Counseling Received'),
        ('maternal_supplements_received', 'Maternal Supplements Received'),
        ('severe_malnutrition_referred', 'Severe Malnutrition Referred'),
        ('male_partner_accompanied_anc', 'Male Partner Accompanied ANC'),
        ('male_partner_participated_counseling', 'Male Partner Participated in Counseling'),
        ('male_partner_hiv_tested', 'Male Partner HIV Tested'),
        ('male_partner_hiv_positive_linked_to_art', 'Male Partner Linked to ART'),
        ('male_partner_supported_referral', 'Male Partner Supported Referral'),
        ('partner_support_for_anc_and_delivery', 'Partner Support for ANC and Facility Delivery'),
        ('men_contribute_to_maternal_nutrition', 'Men Contribute to Maternal Nutrition'),
        ('male_partner_knows_danger_signs', 'Male Partner Knows Danger Signs'),
        ('harmful_gender_norms_reduced', 'Reduced Harmful Gender Norms'),
        ('completed_recommended_anc_visits', 'Completed Recommended ANC Visits'),
        ('adolescent_hiv_tested_and_received_results', 'Adolescent HIV Tested and Received Results'),
        ('adolescent_linked_to_pmtct', 'Adolescent Linked to PMTCT'),
        ('adolescent_received_srhr_counseling', 'Adolescent Received SRHR Counseling'),
        ('adolescent_satisfied_with_anc_yfs', 'Adolescent Satisfied with ANC/YFS'),
        ('adolescent_reported_reduced_stigma', 'Adolescent Reported Reduced Stigma'),
        ('facility_meets_yfs_standards', 'Facility Meets YFS Standards'),
        ('provider_trained_in_yfs', 'Provider Trained in YFS'),
        ('private_confidential_consultation_space', 'Private Consultation Space'),
        ('adolescent_wait_time_minutes', 'Adolescent Wait Time (Minutes)'),
        ('adolescent_received_respectful_care', 'Adolescent Received Respectful Care'),
        ('adolescent_knows_early_anc_and_danger_signs', 'Adolescent Knows Early ANC and Danger Signs'),
        ('adolescent_early_disclosure_and_care_seeking', 'Adolescent Early Disclosure and Care-Seeking'),
        ('date_of_delivery', 'Date of Delivery'),
        ('place_of_delivery', 'Place of Delivery'),
        ('birth_attendant', 'Birth Attendant'),
        ('delivery_type', 'Delivery Type'),
        ('delivery_complications', 'Delivery Complications'),
        ('delivery_outcome', 'Delivery Outcome'),
        ('baby_sex', 'Baby Sex'),
        ('birth_weight_kg', 'Birth Weight (kg)'),
        ('postpartum_checkup_done', 'Postpartum Check-up Done'),
        ('breastfeeding_status', 'Breastfeeding Status'),
        ('family_planning_method', 'Family Planning Method'),
        ('postpartum_complications', 'Postpartum Complications'),
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
