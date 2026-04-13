from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import AgentProfile
from surveys.models import MaternalRecord


class Command(BaseCommand):
    help = 'Create presentation demo data: 5 demo agents with 20 records each.'

    DEMO_AGENT_COUNT = 5
    RECORDS_PER_AGENT = 20
    DEMO_PASSWORD = 'demo12345'

    REGIONS = ['Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Eldoret']
    MUNICIPALITIES = ['Central', 'East', 'West', 'North', 'South']
    PROVINCES = ['Nairobi County', 'Coast County', 'Lake County', 'Rift County', 'Highland County']
    FIRST_NAMES = [
        'Amina', 'Grace', 'Mary', 'Jane', 'Joy', 'Faith', 'Mercy', 'Hellen', 'Irene', 'Naomi',
        'Esther', 'Ruth', 'Lucy', 'Ann', 'Sarah', 'Lilian', 'Martha', 'Zainab', 'Agnes', 'Rose',
    ]
    LAST_NAMES = [
        'Otieno', 'Wanjiku', 'Mwangi', 'Achieng', 'Kiptoo', 'Njeri', 'Auma', 'Chebet', 'Kamau', 'Akinyi',
        'Nyambura', 'Jepkorir', 'Atieno', 'Cherono', 'Wafula', 'Anyango', 'Kariuki', 'Mutheu', 'Naliaka', 'Awuor',
    ]
    FP_METHODS = ['none', 'pills', 'condom', 'injectable', 'implant']
    TT_STATUSES = ['none', 'tt1', 'tt2', 'tt3', 'tt4']
    CIVIL_STATUSES = ['single', 'married', 'live_in']
    EDUCATION_LEVELS = ['elementary', 'high_school', 'senior_high', 'college']
    DELIVERY_TYPES = ['svd', 'cs']
    PLACE_OF_DELIVERY = ['hospital', 'rhu', 'lying_in']
    BIRTH_ATTENDANTS = ['doctor', 'midwife']
    DELIVERY_OUTCOMES = ['live_birth', 'live_birth', 'live_birth', 'stillbirth']
    BREASTFEEDING = ['exclusive', 'mixed', 'none']
    NUTRITION = ['normal', 'underweight', 'normal', 'overweight']

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-existing',
            action='store_true',
            help='Keep existing demo records and only add missing demo users/records.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        keep_existing = options['keep_existing']

        demo_usernames = [f'demo_agent_{index}' for index in range(1, self.DEMO_AGENT_COUNT + 1)]

        if not keep_existing:
            MaternalRecord.objects.filter(agent__username__in=demo_usernames).delete()
            User.objects.filter(username__in=demo_usernames).delete()

        created_agents = []
        today = timezone.localdate()

        for index in range(1, self.DEMO_AGENT_COUNT + 1):
            username = f'demo_agent_{index}'
            region = self.REGIONS[(index - 1) % len(self.REGIONS)]
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': f'Demo{index}',
                    'last_name': 'Agent',
                    'is_active': True,
                    'is_staff': False,
                },
            )
            if created or not user.has_usable_password():
                user.set_password(self.DEMO_PASSWORD)
                user.save()

            profile, _ = AgentProfile.objects.get_or_create(user=user)
            profile.assigned_area = region
            profile.phone_number = f'07000000{index:02d}'
            profile.save()

            created_agents.append(user)

            existing_count = MaternalRecord.objects.filter(agent=user).count()
            records_to_create = max(self.RECORDS_PER_AGENT - existing_count, 0)

            for offset in range(records_to_create):
                record_index = existing_count + offset
                first_name = self.FIRST_NAMES[(record_index + index) % len(self.FIRST_NAMES)]
                last_name = self.LAST_NAMES[(record_index * 2 + index) % len(self.LAST_NAMES)]
                middle_name = chr(65 + ((record_index + index) % 26))
                age = 18 + ((record_index + index) % 20)
                date_collected = today - timedelta(days=(record_index % 12))
                is_pregnant = (record_index % 4) != 0
                prenatal_visits = 1 + (record_index % 6) if is_pregnant else 0
                gravida = 1 + (record_index % 4)
                para = min(gravida, record_index % 3)
                last_delivery_date = date_collected - timedelta(days=280 + (record_index * 15))
                has_delivery_info = (record_index % 3) == 0
                first_ultrasound_weeks = 10 + (record_index % 10) if is_pregnant else None
                high_risk = (record_index % 5) == 0

                MaternalRecord.objects.create(
                    agent=user,
                    is_synced=True,
                    date_collected=date_collected,
                    last_name=last_name,
                    first_name=first_name,
                    middle_name=middle_name,
                    age=age,
                    civil_status=self.CIVIL_STATUSES[record_index % len(self.CIVIL_STATUSES)],
                    address_barangay=region,
                    address_municipality=self.MUNICIPALITIES[(index + record_index) % len(self.MUNICIPALITIES)],
                    address_province=self.PROVINCES[(index - 1) % len(self.PROVINCES)],
                    contact_number=f'07123{index:01d}{record_index:04d}',
                    educational_attainment=self.EDUCATION_LEVELS[record_index % len(self.EDUCATION_LEVELS)],
                    gravida=gravida,
                    para=para,
                    abortion=record_index % 2,
                    living_children=para,
                    last_delivery_date=last_delivery_date,
                    last_delivery_type=self.DELIVERY_TYPES[record_index % len(self.DELIVERY_TYPES)],
                    is_currently_pregnant=is_pregnant,
                    lmp=(date_collected - timedelta(days=(first_ultrasound_weeks or 12) * 7)) if is_pregnant else None,
                    age_of_gestation_weeks=(12 + (record_index % 24)) if is_pregnant else None,
                    expected_date_of_delivery=(date_collected + timedelta(days=140 - (record_index % 30))) if is_pregnant else None,
                    prenatal_visit_count=prenatal_visits,
                    prenatal_facility=f'{region} Health Centre',
                    weight_kg=55 + (record_index % 15),
                    height_cm=150 + (record_index % 20),
                    blood_pressure=f'{110 + (record_index % 20)}/{70 + (record_index % 10)}',
                    hemoglobin_level=10 + ((record_index % 5) * 0.5),
                    nutritional_status=self.NUTRITION[record_index % len(self.NUTRITION)],
                    tetanus_toxoid_status=self.TT_STATUSES[record_index % len(self.TT_STATUSES)],
                    iron_supplementation=(record_index % 2) == 0,
                    vitamin_a_supplementation=(record_index % 4) == 0,
                    dental_checkup=(record_index % 6) == 0,
                    family_planning_counseling=(record_index % 3) == 0,
                    first_ultrasound_current_pregnancy=is_pregnant and (record_index % 2 == 0),
                    previous_pregnancies_with_ultrasound=gravida > 1 and (record_index % 2 == 0),
                    previous_pregnancies_with_ultrasound_count=(gravida - 1) if (gravida > 1 and (record_index % 2 == 0)) else None,
                    ultrasound_service_helpful=(record_index % 5) != 0,
                    benefit_saves_travel_time=(record_index % 2) == 0,
                    benefit_reduces_transport_costs=(record_index % 3) == 0,
                    benefit_detects_problems_early=(record_index % 2) == 0,
                    benefit_understands_baby_health=(record_index % 4) != 0,
                    benefit_encourages_anc=(record_index % 3) != 1,
                    benefit_enables_early_referral=high_risk,
                    benefit_knows_due_date=(record_index % 2) == 1,
                    benefit_other='Helped reassure me about baby movement.' if (record_index % 8 == 0) else '',
                    ultrasound_before_24_weeks=is_pregnant and (first_ultrasound_weeks is not None and first_ultrasound_weeks < 24),
                    ultrasound_screened_high_risk=is_pregnant and (record_index % 2 == 0),
                    complication_placenta_previa=high_risk and (record_index % 2 == 0),
                    complication_multiple_gestation=high_risk and (record_index % 3 == 0),
                    complication_breech=high_risk and (record_index % 4 == 0),
                    complication_other='Anemia risk noted' if (record_index % 7 == 0) else '',
                    first_ultrasound_gestation_weeks=first_ultrasound_weeks,
                    high_risk_pregnancy=high_risk,
                    high_risk_identified_through_ruaa=high_risk,
                    referred_high_risk_pregnancy=high_risk,
                    referral_completed=high_risk and (record_index % 2 == 0),
                    referral_received_appropriate_care=high_risk and (record_index % 2 == 0),
                    referral_reason_obstetric_complication=high_risk and (record_index % 2 == 0),
                    referral_reason_no_fetal_heartbeat=high_risk and (record_index % 11 == 0),
                    referral_reason_malpresentation=high_risk and (record_index % 4 == 0),
                    referral_reason_multiple_pregnancy=high_risk and (record_index % 3 == 0),
                    referral_reason_hiv_related=high_risk and (record_index % 13 == 0),
                    referral_reason_severe_anemia_malnutrition=high_risk and (record_index % 5 == 0),
                    referral_reason_other='Reduced fetal movement' if high_risk and (record_index % 9 == 0) else '',
                    gbv_asked_about_safety=(record_index % 3) == 0,
                    gbv_respectful_supportive_provider=(record_index % 4) != 0,
                    gbv_given_information_for_help=(record_index % 5) == 0,
                    gbv_offered_help_or_referral=None if (record_index % 6 == 0) else ((record_index % 2) == 0),
                    gbv_felt_safe_discussing_issues=(record_index % 3) != 1,
                    nutrition_counseling_received=(record_index % 2) == 0,
                    maternal_supplements_received=(record_index % 3) != 0,
                    severe_malnutrition_referred=(record_index % 10) == 0,
                    nutrition_discussed_foods=(record_index % 2) == 0,
                    nutrition_advised_iron_folic=(record_index % 3) != 1,
                    nutrition_understands_important_foods=(record_index % 4) != 0,
                    nutrition_improved_diet_since_visit=(record_index % 3) == 0,
                    fp_discussed_options=(record_index % 2) == 0,
                    fp_methods_explained_clearly=(record_index % 4) != 0,
                    fp_understands_post_delivery_options=(record_index % 3) != 1,
                    fp_given_opportunity_to_ask_questions=(record_index % 5) != 0,
                    sti_discussed_infections=(record_index % 2) == 1,
                    sti_asked_about_symptoms=(record_index % 4) == 0,
                    sti_advised_on_prevention=(record_index % 3) != 2,
                    sti_offered_testing_or_treatment=None if (record_index % 6 == 0) else ((record_index % 2) == 0),
                    client_treated_with_respect=(record_index % 5) != 0,
                    client_explanations_clear=(record_index % 4) != 1,
                    client_visit_helped_understand_health=(record_index % 3) != 0,
                    client_most_helpful_feedback='Understanding my baby and due date better.' if (record_index % 2 == 0) else 'The respectful explanation from the provider.',
                    date_of_delivery=(date_collected - timedelta(days=record_index + 7)) if has_delivery_info else None,
                    place_of_delivery=self.PLACE_OF_DELIVERY[record_index % len(self.PLACE_OF_DELIVERY)] if has_delivery_info else '',
                    birth_attendant=self.BIRTH_ATTENDANTS[record_index % len(self.BIRTH_ATTENDANTS)] if has_delivery_info else '',
                    delivery_type=self.DELIVERY_TYPES[record_index % len(self.DELIVERY_TYPES)] if has_delivery_info else '',
                    delivery_complications='Mild bleeding managed' if has_delivery_info and (record_index % 5 == 0) else '',
                    delivery_outcome=self.DELIVERY_OUTCOMES[record_index % len(self.DELIVERY_OUTCOMES)] if has_delivery_info else '',
                    baby_sex='female' if (record_index % 2 == 0) else 'male',
                    birth_weight_kg=2.5 + ((record_index % 8) * 0.2) if has_delivery_info else None,
                    postpartum_checkup_done=has_delivery_info and (record_index % 2 == 0),
                    breastfeeding_status=self.BREASTFEEDING[record_index % len(self.BREASTFEEDING)] if has_delivery_info else '',
                    family_planning_method=self.FP_METHODS[record_index % len(self.FP_METHODS)] if has_delivery_info else 'none',
                    postpartum_complications='None' if has_delivery_info and (record_index % 4 != 0) else '',
                    notes=f'Demo record {record_index + 1} for client presentation.',
                )

        self.stdout.write(self.style.SUCCESS(
            f'Created demo data for {len(created_agents)} agents with {self.RECORDS_PER_AGENT} records each.'
        ))
        self.stdout.write(self.style.WARNING(
            f'Demo agent password for all demo agents: {self.DEMO_PASSWORD}'
        ))
