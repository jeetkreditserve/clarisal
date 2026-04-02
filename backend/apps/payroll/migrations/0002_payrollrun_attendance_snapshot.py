from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrollrun',
            name='attendance_snapshot',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
