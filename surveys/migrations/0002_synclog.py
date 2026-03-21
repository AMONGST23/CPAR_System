from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('surveys', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SyncLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('running', 'Running'), ('success', 'Success'), ('partial', 'Partial'), ('failed', 'Failed'), ('skipped', 'Skipped')], default='running', max_length=20)),
                ('records_attempted', models.PositiveIntegerField(default=0)),
                ('records_synced', models.PositiveIntegerField(default=0)),
                ('records_failed', models.PositiveIntegerField(default=0)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('message', models.CharField(blank=True, max_length=255)),
                ('error_details', models.JSONField(blank=True, default=dict)),
            ],
            options={
                'ordering': ['-started_at'],
            },
        ),
    ]
