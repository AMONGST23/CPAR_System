import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MaternalRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sync_uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('is_synced', models.BooleanField(default=False)),
                ('date_collected', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_name', models.CharField(max_length=100)),
                ('first_name', models.CharField(max_length=100)),
                ('middle_name', models.CharField(blank=True, max_length=100)),
                ('date_of_birth', models.DateField(blank=True, null=True)),
                ('age', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('civil_status', models.CharField(blank=True, choices=[('single', 'Single'), ('married', 'Married'), ('widowed', 'Widowed'), ('separated', 'Separated'), ('live_in', 'Live-in')], max_length=20)),
                ('address_barangay', models.CharField(blank=True, max_length=100)),
                ('address_municipality', models.CharField(blank=True, max_length=100)),
                ('address_province', models.CharField(blank=True, max_length=100)),
                ('contact_number', models.CharField(blank=True, max_length=20)),
                ('educational_attainment', models.CharField(blank=True, choices=[('none', 'No formal education'), ('elementary', 'Elementary'), ('high_school', 'High School'), ('senior_high', 'Senior High School'), ('vocational', 'Vocational/Technical'), ('college', 'College'), ('post_grad', 'Post Graduate')], max_length=20)),
                ('gravida', models.PositiveSmallIntegerField(blank=True, help_text='Total number of pregnancies', null=True)),
                ('para', models.PositiveSmallIntegerField(blank=True, help_text='Number of deliveries', null=True)),
                ('abortion', models.PositiveSmallIntegerField(blank=True, help_text='Number of miscarriages/abortions', null=True)),
                ('living_children', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('last_delivery_date', models.DateField(blank=True, null=True)),
                ('last_delivery_type', models.CharField(blank=True, choices=[('svd', 'Normal/SVD'), ('cs', 'Cesarean Section'), ('forceps', 'Forceps/Vacuum')], max_length=10)),
                ('is_currently_pregnant', models.BooleanField(default=False)),
                ('lmp', models.DateField(blank=True, null=True, verbose_name='Last Menstrual Period')),
                ('age_of_gestation_weeks', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Age of Gestation (weeks)')),
                ('expected_date_of_delivery', models.DateField(blank=True, null=True, verbose_name='Expected Date of Delivery')),
                ('prenatal_visit_count', models.PositiveSmallIntegerField(blank=True, default=0, null=True)),
                ('prenatal_facility', models.CharField(blank=True, max_length=200)),
                ('weight_kg', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('height_cm', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('blood_pressure', models.CharField(blank=True, help_text='e.g. 120/80', max_length=20)),
                ('hemoglobin_level', models.DecimalField(blank=True, decimal_places=2, help_text='g/dL', max_digits=5, null=True)),
                ('nutritional_status', models.CharField(blank=True, choices=[('normal', 'Normal'), ('underweight', 'Underweight'), ('overweight', 'Overweight'), ('obese', 'Obese')], max_length=15)),
                ('tetanus_toxoid_status', models.CharField(choices=[('none', 'None'), ('tt1', 'TT1'), ('tt2', 'TT2'), ('tt3', 'TT3'), ('tt4', 'TT4'), ('tt5', 'TT5/Completed')], default='none', max_length=5)),
                ('iron_supplementation', models.BooleanField(default=False)),
                ('vitamin_a_supplementation', models.BooleanField(default=False)),
                ('dental_checkup', models.BooleanField(default=False)),
                ('family_planning_counseling', models.BooleanField(default=False)),
                ('date_of_delivery', models.DateField(blank=True, null=True)),
                ('place_of_delivery', models.CharField(blank=True, choices=[('hospital', 'Hospital'), ('rhu', 'RHU/Health Center'), ('lying_in', 'Lying-in Clinic'), ('home', 'Home'), ('others', 'Others')], max_length=10)),
                ('birth_attendant', models.CharField(blank=True, choices=[('doctor', 'Doctor'), ('midwife', 'Nurse/Midwife'), ('hilot', 'Hilot/Traditional Birth Attendant'), ('others', 'Others')], max_length=10)),
                ('delivery_type', models.CharField(blank=True, choices=[('svd', 'Normal/SVD'), ('cs', 'Cesarean Section'), ('forceps', 'Forceps/Vacuum')], max_length=10)),
                ('delivery_complications', models.TextField(blank=True)),
                ('delivery_outcome', models.CharField(blank=True, choices=[('live_birth', 'Live Birth'), ('stillbirth', 'Stillbirth'), ('miscarriage', 'Miscarriage')], max_length=15)),
                ('baby_sex', models.CharField(blank=True, choices=[('male', 'Male'), ('female', 'Female')], max_length=6)),
                ('birth_weight_kg', models.DecimalField(blank=True, decimal_places=3, max_digits=4, null=True)),
                ('postpartum_checkup_done', models.BooleanField(default=False)),
                ('breastfeeding_status', models.CharField(blank=True, choices=[('exclusive', 'Exclusive Breastfeeding'), ('mixed', 'Mixed Feeding'), ('none', 'Not Breastfeeding')], max_length=10)),
                ('family_planning_method', models.CharField(choices=[('none', 'None'), ('pills', 'Pills'), ('condom', 'Condom'), ('iud', 'IUD'), ('injectable', 'Injectable'), ('implant', 'Implant'), ('nfp', 'Natural Family Planning'), ('ligation', 'Ligation/BTL'), ('vasectomy', 'Vasectomy'), ('others', 'Others')], default='none', max_length=15)),
                ('postpartum_complications', models.TextField(blank=True)),
                ('notes', models.TextField(blank=True)),
                ('agent', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='records', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Maternal Record',
                'verbose_name_plural': 'Maternal Records',
                'ordering': ['-date_collected', '-created_at'],
            },
        ),
    ]
