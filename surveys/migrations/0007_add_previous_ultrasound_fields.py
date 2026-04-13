from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('surveys', '0006_remove_maternalrecord_adolescent_early_disclosure_and_care_seeking_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='maternalrecord',
            name='previous_pregnancies_with_ultrasound',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='maternalrecord',
            name='previous_pregnancies_with_ultrasound_count',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
