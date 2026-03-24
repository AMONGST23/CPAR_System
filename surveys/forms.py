import datetime

from django import forms
from django.core.exceptions import ValidationError

from .models import MaternalRecord


class MaternalRecordForm(forms.ModelForm):
    class Meta:
        model = MaternalRecord
        exclude = ['agent', 'sync_uuid', 'is_synced', 'created_at', 'updated_at']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-input'}),
            'age': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'max': 120}),
            'civil_status': forms.Select(attrs={'class': 'form-select'}),
            'address_barangay': forms.TextInput(attrs={'class': 'form-input'}),
            'address_municipality': forms.TextInput(attrs={'class': 'form-input'}),
            'address_province': forms.TextInput(attrs={'class': 'form-input'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-input', 'inputmode': 'tel'}),
            'educational_attainment': forms.Select(attrs={'class': 'form-select'}),
            'gravida': forms.NumberInput(attrs={'class': 'form-input', 'min': 0}),
            'para': forms.NumberInput(attrs={'class': 'form-input', 'min': 0}),
            'abortion': forms.NumberInput(attrs={'class': 'form-input', 'min': 0}),
            'living_children': forms.NumberInput(attrs={'class': 'form-input', 'min': 0}),
            'last_delivery_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'last_delivery_type': forms.Select(attrs={'class': 'form-select'}),
            'lmp': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'age_of_gestation_weeks': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'max': 45}),
            'expected_date_of_delivery': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'prenatal_visit_count': forms.NumberInput(attrs={'class': 'form-input', 'min': 0}),
            'prenatal_facility': forms.TextInput(attrs={'class': 'form-input'}),
            'weight_kg': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': 0}),
            'height_cm': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': 0}),
            'blood_pressure': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '120/80'}),
            'hemoglobin_level': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': 0}),
            'nutritional_status': forms.Select(attrs={'class': 'form-select'}),
            'tetanus_toxoid_status': forms.Select(attrs={'class': 'form-select'}),
            'complication_other': forms.TextInput(attrs={'class': 'form-input'}),
            'first_ultrasound_gestation_weeks': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'max': 45}),
            'date_of_delivery': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'place_of_delivery': forms.Select(attrs={'class': 'form-select'}),
            'birth_attendant': forms.Select(attrs={'class': 'form-select'}),
            'delivery_type': forms.Select(attrs={'class': 'form-select'}),
            'delivery_complications': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
            'delivery_outcome': forms.Select(attrs={'class': 'form-select'}),
            'baby_sex': forms.Select(attrs={'class': 'form-select'}),
            'birth_weight_kg': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.001', 'min': 0}),
            'breastfeeding_status': forms.Select(attrs={'class': 'form-select'}),
            'family_planning_method': forms.Select(attrs={'class': 'form-select'}),
            'postpartum_complications': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
            'adolescent_wait_time_minutes': forms.NumberInput(attrs={'class': 'form-input', 'min': 0}),
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

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data.get('is_currently_pregnant'):
            cleaned_data['lmp'] = None
            cleaned_data['age_of_gestation_weeks'] = None
            cleaned_data['expected_date_of_delivery'] = None
            cleaned_data['prenatal_visit_count'] = 0
            cleaned_data['prenatal_facility'] = ''

        if (
            cleaned_data.get('date_of_delivery')
            and cleaned_data.get('delivery_outcome')
            and not cleaned_data.get('delivery_type')
        ):
            self.add_error('delivery_type', 'Delivery type is required when delivery details are recorded.')

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
