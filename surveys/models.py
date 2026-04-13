import uuid

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models

from .crypto import decrypt_value, encrypt_value


class MaternalRecord(models.Model):
    """Maternal health data collection record."""

    ENCRYPTED_FIELDS = (
        'last_name',
        'first_name',
        'middle_name',
        'address_barangay',
        'address_municipality',
        'address_province',
        'contact_number',
    )

    # Meta / tracking
    sync_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_synced = models.BooleanField(default=False)
    agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='records')
    date_collected = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Section A: Respondent Information
    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    age = models.PositiveSmallIntegerField(null=True, blank=True)

    MARITAL_STATUS_CHOICES = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('widowed', 'Widowed'),
        ('separated', 'Separated'),
        ('live_in', 'Live-in'),
    ]
    civil_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES, blank=True)

    address_barangay = models.CharField(max_length=100, blank=True)
    address_municipality = models.CharField(max_length=100, blank=True)
    address_province = models.CharField(max_length=100, blank=True)
    contact_number = models.CharField(max_length=20, blank=True)

    EDUCATION_CHOICES = [
        ('none', 'No formal education'),
        ('elementary', 'Elementary'),
        ('high_school', 'High School'),
        ('senior_high', 'Senior High School'),
        ('vocational', 'Vocational/Technical'),
        ('college', 'College'),
        ('post_grad', 'Post Graduate'),
    ]
    educational_attainment = models.CharField(max_length=20, choices=EDUCATION_CHOICES, blank=True)

    # Section B: Obstetric History
    gravida = models.PositiveSmallIntegerField(null=True, blank=True, help_text='Total number of pregnancies')
    para = models.PositiveSmallIntegerField(null=True, blank=True, help_text='Number of deliveries')
    abortion = models.PositiveSmallIntegerField(null=True, blank=True, help_text='Number of miscarriages/abortions')
    living_children = models.PositiveSmallIntegerField(null=True, blank=True)
    last_delivery_date = models.DateField(null=True, blank=True)

    DELIVERY_TYPE_CHOICES = [
        ('svd', 'Normal/SVD'),
        ('cs', 'Cesarean Section'),
        ('forceps', 'Forceps/Vacuum'),
    ]
    last_delivery_type = models.CharField(max_length=10, choices=DELIVERY_TYPE_CHOICES, blank=True)

    # Section C: Current Pregnancy
    is_currently_pregnant = models.BooleanField(default=False)
    lmp = models.DateField(null=True, blank=True, verbose_name='Last Menstrual Period')
    age_of_gestation_weeks = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='Age of Gestation (weeks)',
    )
    expected_date_of_delivery = models.DateField(
        null=True,
        blank=True,
        verbose_name='Expected Date of Delivery',
    )
    prenatal_visit_count = models.PositiveSmallIntegerField(null=True, blank=True, default=0)
    prenatal_facility = models.CharField(max_length=200, blank=True)

    # Section D: Health Assessment
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    blood_pressure = models.CharField(max_length=20, blank=True, help_text='e.g. 120/80')
    hemoglobin_level = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='g/dL',
    )

    NUTRITIONAL_STATUS_CHOICES = [
        ('normal', 'Normal'),
        ('underweight', 'Underweight'),
        ('overweight', 'Overweight'),
        ('obese', 'Obese'),
    ]
    nutritional_status = models.CharField(max_length=15, choices=NUTRITIONAL_STATUS_CHOICES, blank=True)

    # Section E: Services Received
    TT_STATUS_CHOICES = [
        ('none', 'None'),
        ('tt1', 'TT1'),
        ('tt2', 'TT2'),
        ('tt3', 'TT3'),
        ('tt4', 'TT4'),
        ('tt5', 'TT5/Completed'),
    ]
    tetanus_toxoid_status = models.CharField(max_length=5, choices=TT_STATUS_CHOICES, default='none', blank=True)
    iron_supplementation = models.BooleanField(default=False)
    vitamin_a_supplementation = models.BooleanField(default=False)
    dental_checkup = models.BooleanField(default=False)
    family_planning_counseling = models.BooleanField(default=False)

    # Section F: Ultrasound, Risk Detection, and Referral
    first_ultrasound_current_pregnancy = models.BooleanField(default=False)
    previous_pregnancies_with_ultrasound = models.BooleanField(default=False)
    previous_pregnancies_with_ultrasound_count = models.PositiveSmallIntegerField(null=True, blank=True)
    ultrasound_service_helpful = models.BooleanField(default=False)
    benefit_saves_travel_time = models.BooleanField(default=False)
    benefit_reduces_transport_costs = models.BooleanField(default=False)
    benefit_detects_problems_early = models.BooleanField(default=False)
    benefit_understands_baby_health = models.BooleanField(default=False)
    benefit_encourages_anc = models.BooleanField(default=False)
    benefit_enables_early_referral = models.BooleanField(default=False)
    benefit_knows_due_date = models.BooleanField(default=False)
    benefit_other = models.CharField(max_length=255, blank=True)
    ultrasound_before_24_weeks = models.BooleanField(default=False)
    ultrasound_screened_high_risk = models.BooleanField(default=False)
    complication_placenta_previa = models.BooleanField(default=False)
    complication_multiple_gestation = models.BooleanField(default=False)
    complication_breech = models.BooleanField(default=False)
    complication_other = models.CharField(max_length=255, blank=True)
    first_ultrasound_gestation_weeks = models.PositiveSmallIntegerField(null=True, blank=True)
    high_risk_pregnancy = models.BooleanField(default=False)
    high_risk_identified_through_ruaa = models.BooleanField(default=False)
    referred_high_risk_pregnancy = models.BooleanField(default=False)
    referral_completed = models.BooleanField(default=False)
    referral_received_appropriate_care = models.BooleanField(default=False)
    referral_reason_obstetric_complication = models.BooleanField(default=False)
    referral_reason_no_fetal_heartbeat = models.BooleanField(default=False)
    referral_reason_malpresentation = models.BooleanField(default=False)
    referral_reason_multiple_pregnancy = models.BooleanField(default=False)
    referral_reason_hiv_related = models.BooleanField(default=False)
    referral_reason_severe_anemia_malnutrition = models.BooleanField(default=False)
    referral_reason_other = models.CharField(max_length=255, blank=True)

    # Section G: GBV Response
    gbv_asked_about_safety = models.BooleanField(default=False)
    gbv_respectful_supportive_provider = models.BooleanField(default=False)
    gbv_given_information_for_help = models.BooleanField(default=False)
    gbv_offered_help_or_referral = models.BooleanField(null=True, blank=True)
    gbv_felt_safe_discussing_issues = models.BooleanField(default=False)

    # Section H: Nutrition
    nutrition_counseling_received = models.BooleanField(default=False)
    maternal_supplements_received = models.BooleanField(default=False)
    severe_malnutrition_referred = models.BooleanField(default=False)
    nutrition_discussed_foods = models.BooleanField(default=False)
    nutrition_advised_iron_folic = models.BooleanField(default=False)
    nutrition_understands_important_foods = models.BooleanField(default=False)
    nutrition_improved_diet_since_visit = models.BooleanField(default=False)

    # Section H: Family Planning and STI
    fp_discussed_options = models.BooleanField(default=False)
    fp_methods_explained_clearly = models.BooleanField(default=False)
    fp_understands_post_delivery_options = models.BooleanField(default=False)
    fp_given_opportunity_to_ask_questions = models.BooleanField(default=False)
    sti_discussed_infections = models.BooleanField(default=False)
    sti_asked_about_symptoms = models.BooleanField(default=False)
    sti_advised_on_prevention = models.BooleanField(default=False)
    sti_offered_testing_or_treatment = models.BooleanField(null=True, blank=True)

    # Section I: Cross-Cutting Client Experience
    client_treated_with_respect = models.BooleanField(default=False)
    client_explanations_clear = models.BooleanField(default=False)
    client_visit_helped_understand_health = models.BooleanField(default=False)
    client_most_helpful_feedback = models.TextField(blank=True)

    # Section F: Delivery Information
    date_of_delivery = models.DateField(null=True, blank=True)

    PLACE_OF_DELIVERY_CHOICES = [
        ('hospital', 'Hospital'),
        ('rhu', 'RHU/Health Center'),
        ('lying_in', 'Lying-in Clinic'),
        ('home', 'Home'),
        ('others', 'Others'),
    ]
    place_of_delivery = models.CharField(max_length=10, choices=PLACE_OF_DELIVERY_CHOICES, blank=True)

    BIRTH_ATTENDANT_CHOICES = [
        ('doctor', 'Doctor'),
        ('midwife', 'Nurse/Midwife'),
        ('hilot', 'Hilot/Traditional Birth Attendant'),
        ('others', 'Others'),
    ]
    birth_attendant = models.CharField(max_length=10, choices=BIRTH_ATTENDANT_CHOICES, blank=True)
    delivery_type = models.CharField(max_length=10, choices=DELIVERY_TYPE_CHOICES, blank=True)
    delivery_complications = models.TextField(blank=True)

    OUTCOME_CHOICES = [
        ('live_birth', 'Live Birth'),
        ('stillbirth', 'Stillbirth'),
        ('miscarriage', 'Miscarriage'),
    ]
    delivery_outcome = models.CharField(max_length=15, choices=OUTCOME_CHOICES, blank=True)

    SEX_CHOICES = [('male', 'Male'), ('female', 'Female')]
    baby_sex = models.CharField(max_length=6, choices=SEX_CHOICES, blank=True)
    birth_weight_kg = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)

    # Section G: Postpartum
    postpartum_checkup_done = models.BooleanField(default=False)

    BREASTFEEDING_CHOICES = [
        ('exclusive', 'Exclusive Breastfeeding'),
        ('mixed', 'Mixed Feeding'),
        ('none', 'Not Breastfeeding'),
    ]
    breastfeeding_status = models.CharField(max_length=10, choices=BREASTFEEDING_CHOICES, blank=True)

    FP_METHOD_CHOICES = [
        ('none', 'None'),
        ('pills', 'Pills'),
        ('condom', 'Condom'),
        ('iud', 'IUD'),
        ('injectable', 'Injectable'),
        ('implant', 'Implant'),
        ('nfp', 'Natural Family Planning'),
        ('ligation', 'Ligation/BTL'),
        ('vasectomy', 'Vasectomy'),
        ('others', 'Others'),
    ]
    family_planning_method = models.CharField(max_length=15, choices=FP_METHOD_CHOICES, default='none', blank=True)
    postpartum_complications = models.TextField(blank=True)

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date_collected', '-created_at']
        verbose_name = 'Maternal Record'
        verbose_name_plural = 'Maternal Records'

    def __str__(self):
        return f"{self.last_name}, {self.first_name} ({self.date_collected})"

    @property
    def full_name(self):
        name = f"{self.last_name}, {self.first_name}"
        if self.middle_name:
            name = f"{name} {self.middle_name[0]}."
        return name

    def clean(self):
        errors = {}

        if self.last_delivery_date and self.date_collected and self.last_delivery_date > self.date_collected:
            errors['last_delivery_date'] = 'Last delivery date cannot be after the collection date.'

        if self.date_of_delivery and self.date_collected and self.date_of_delivery > self.date_collected:
            errors['date_of_delivery'] = 'Date of delivery cannot be after the collection date.'

        if self.para is not None and self.gravida is not None and self.para > self.gravida:
            errors['para'] = 'Para cannot be greater than gravida.'

        if self.is_currently_pregnant:
            if not self.lmp and not self.expected_date_of_delivery:
                errors['lmp'] = 'Provide LMP or expected date of delivery for a current pregnancy.'
        else:
            pregnancy_fields = [
                self.lmp,
                self.age_of_gestation_weeks,
                self.expected_date_of_delivery,
                self.prenatal_visit_count,
                self.prenatal_facility,
            ]
            if any(value not in (None, '', 0) for value in pregnancy_fields):
                errors['is_currently_pregnant'] = 'Pregnancy details should only be filled for current pregnancies.'

        if self.previous_pregnancies_with_ultrasound:
            if self.previous_pregnancies_with_ultrasound_count in (None, ''):
                errors['previous_pregnancies_with_ultrasound_count'] = (
                    'Enter how many previous pregnancies included an ultrasound.'
                )
        elif self.previous_pregnancies_with_ultrasound_count not in (None, ''):
            errors['previous_pregnancies_with_ultrasound'] = (
                'Only enter a number if previous pregnancies included an ultrasound.'
            )

        if errors:
            raise ValidationError(errors)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._decrypt_sensitive_fields()

    def _decrypt_sensitive_fields(self):
        for field_name in self.ENCRYPTED_FIELDS:
            setattr(self, field_name, decrypt_value(getattr(self, field_name, '')))

    def _encrypt_sensitive_fields(self):
        original_values = {}
        for field_name in self.ENCRYPTED_FIELDS:
            original_values[field_name] = getattr(self, field_name, '')
            setattr(self, field_name, encrypt_value(original_values[field_name]))
        return original_values

    def save(self, *args, **kwargs):
        original_values = self._encrypt_sensitive_fields()
        try:
            return super().save(*args, **kwargs)
        finally:
            for field_name, value in original_values.items():
                setattr(self, field_name, value)


class SyncLog(models.Model):
    STATUS_RUNNING = 'running'
    STATUS_SUCCESS = 'success'
    STATUS_PARTIAL = 'partial'
    STATUS_FAILED = 'failed'
    STATUS_SKIPPED = 'skipped'

    STATUS_CHOICES = [
        (STATUS_RUNNING, 'Running'),
        (STATUS_SUCCESS, 'Success'),
        (STATUS_PARTIAL, 'Partial'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_SKIPPED, 'Skipped'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RUNNING)
    records_attempted = models.PositiveIntegerField(default=0)
    records_synced = models.PositiveIntegerField(default=0)
    records_failed = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    message = models.CharField(max_length=255, blank=True)
    error_details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.get_status_display()} sync at {self.started_at:%Y-%m-%d %H:%M}"
