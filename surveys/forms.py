import datetime

from django import forms
from django.core.exceptions import ValidationError

from .models import MaternalRecord


class MaternalRecordForm(forms.ModelForm):
    YES_NO_CHOICES = (
        ('true', 'Yes'),
        ('false', 'No'),
    )
    YES_NO_NA_CHOICES = (
        ('', 'Not applicable'),
        ('true', 'Yes'),
        ('false', 'No'),
    )

    class Meta:
        model = MaternalRecord
        exclude = ['agent', 'sync_uuid', 'is_synced', 'created_at', 'updated_at']
        widgets = {
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-input'}),
            'age': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'max': 120}),
            'civil_status': forms.Select(attrs={'class': 'form-select'}),
            'occupation': forms.Select(attrs={'class': 'form-select'}),
            'address_barangay': forms.TextInput(attrs={'class': 'form-input'}),
            'address_municipality': forms.TextInput(attrs={'class': 'form-input'}),
            'address_province': forms.TextInput(attrs={'class': 'form-input'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-input', 'inputmode': 'tel'}),
            'gravida': forms.NumberInput(attrs={'class': 'form-input', 'min': 0}),
            'para': forms.NumberInput(attrs={'class': 'form-input', 'min': 0}),
            'abortion': forms.NumberInput(attrs={'class': 'form-input', 'min': 0}),
            'living_children': forms.NumberInput(attrs={'class': 'form-input', 'min': 0}),
            'last_delivery_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'last_delivery_type': forms.Select(attrs={'class': 'form-select'}),
            'last_delivery_location': forms.Select(attrs={'class': 'form-select'}),
            'home_delivery_support': forms.Select(attrs={'class': 'form-select'}),
            'lmp': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'age_of_gestation_weeks': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'max': 45}),
            'expected_date_of_delivery': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'prenatal_visit_count': forms.NumberInput(attrs={'class': 'form-input', 'min': 0}),
            'prenatal_facility': forms.Select(attrs={'class': 'form-select'}),
            'weight_kg': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': 0}),
            'height_cm': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': 0}),
            'blood_pressure': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '120/80'}),
            'hemoglobin_level': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': 0}),
            'nutritional_status': forms.Select(attrs={'class': 'form-select'}),
            'tetanus_toxoid_status': forms.Select(attrs={'class': 'form-select'}),
            'previous_pregnancies_with_ultrasound_count': forms.NumberInput(attrs={'class': 'form-input', 'min': 0}),
            'complication_other': forms.TextInput(attrs={'class': 'form-input'}),
            'first_ultrasound_gestation_weeks': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'max': 45}),
            'benefit_other': forms.TextInput(attrs={'class': 'form-input'}),
            'referral_reason_other': forms.TextInput(attrs={'class': 'form-input'}),
            'client_most_helpful_feedback': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'date_collected': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['date_collected'].initial = datetime.date.today()
        self.fields['last_name'].required = True
        self.fields['first_name'].required = True
        self.fields['date_collected'].required = True
        yes_no_fields = (
            'first_ultrasound_current_pregnancy',
            'ultrasound_before_24_weeks',
            'ultrasound_screened_high_risk',
            'ultrasound_service_helpful',
            'benefit_saves_travel_time',
            'benefit_detects_problems_early',
            'benefit_understands_baby_health',
            'benefit_encourages_anc',
            'benefit_enables_early_referral',
            'benefit_knows_due_date',
            'high_risk_pregnancy',
            'referred_high_risk_pregnancy',
        )
        for field_name in yes_no_fields:
            current_value = self.initial.get(field_name, getattr(self.instance, field_name, False))
            initial_value = 'true' if current_value else 'false'
            self.fields[field_name] = forms.TypedChoiceField(
                choices=self.YES_NO_CHOICES,
                required=False,
                coerce=lambda value: value == 'true',
                widget=forms.Select(attrs={'class': 'form-select'}),
                initial=initial_value,
            )
        for field_name in ('gbv_offered_help_or_referral', 'sti_offered_testing_or_treatment'):
            current_value = self.initial.get(field_name, getattr(self.instance, field_name, None))
            initial_value = {True: 'true', False: 'false'}.get(current_value, '')
            self.fields[field_name] = forms.TypedChoiceField(
                choices=self.YES_NO_NA_CHOICES,
                required=False,
                coerce=lambda value: {'true': True, 'false': False}.get(value),
                empty_value=None,
                widget=forms.Select(attrs={'class': 'form-select'}),
                initial=initial_value,
            )

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data.get('is_currently_pregnant'):
            cleaned_data['lmp'] = None
            cleaned_data['age_of_gestation_weeks'] = None
            cleaned_data['expected_date_of_delivery'] = None
            cleaned_data['prenatal_visit_count'] = 0
            cleaned_data['prenatal_facility'] = ''

        if not cleaned_data.get('previous_pregnancies_with_ultrasound'):
            cleaned_data['previous_pregnancies_with_ultrasound_count'] = None

        if cleaned_data.get('last_delivery_location') != 'home':
            cleaned_data['home_delivery_support'] = ''

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        try:
            excluded_fields = list(self._meta.exclude or [])
            instance.full_clean(exclude=excluded_fields)
        except ValidationError as exc:
            self._update_errors(exc)
            raise

        if commit:
            instance.save()
        return instance
