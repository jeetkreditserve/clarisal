from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0002_payrollrun_attendance_snapshot'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrollrun',
            name='use_attendance_inputs',
            field=models.BooleanField(default=False),
        ),
    ]
