from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('surveys', '0007_add_previous_ultrasound_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='maternalrecord',
            name='occupation',
            field=models.CharField(
                blank=True,
                choices=[
                    ('farmer', 'Farmer'),
                    ('employed', 'Employed'),
                    ('self_employed', 'Self Employed'),
                    ('not_employed', 'Not Employed'),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='maternalrecord',
            name='last_delivery_location',
            field=models.CharField(
                blank=True,
                choices=[('health_facility', 'Health Facility'), ('home', 'Home')],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='maternalrecord',
            name='home_delivery_support',
            field=models.CharField(
                blank=True,
                choices=[('tba', 'TBA'), ('self', 'SELF')],
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='maternalrecord',
            name='pmtct_checked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='maternalrecord',
            name='stds_checked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='maternalrecord',
            name='referral_reason_ectopic_pregnancy',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='maternalrecord',
            name='referral_reason_placental_abnormalities',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='maternalrecord',
            name='referral_reason_amniotic_fluid_disorders',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='maternalrecord',
            name='referral_reason_uterine_pathologies',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='maternalrecord',
            name='referral_reason_fetal_distress',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='maternalrecord',
            name='gbv_encountered',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='maternalrecord',
            name='gbv_shared_concern',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='maternalrecord',
            name='abortion',
            field=models.PositiveSmallIntegerField(blank=True, help_text='Number of miscarriages', null=True),
        ),
        migrations.AlterField(
            model_name='maternalrecord',
            name='educational_attainment',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AlterField(
            model_name='maternalrecord',
            name='prenatal_facility',
            field=models.CharField(
                blank=True,
                choices=[
                    ('dispensary', 'Dispensary'),
                    ('health_center', 'Health center'),
                    ('hospital', 'Hospital'),
                ],
                max_length=20,
            ),
        ),
    ]
