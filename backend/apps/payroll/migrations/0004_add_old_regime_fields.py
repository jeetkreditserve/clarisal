from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0003_payrollrun_use_attendance_inputs'),
    ]

    operations = [
        migrations.AddField(
            model_name='compensationassignment',
            name='tax_regime',
            field=models.CharField(
                choices=[('NEW', 'New Regime'), ('OLD', 'Old Regime')],
                default='NEW',
                max_length=3,
            ),
        ),
        migrations.AddField(
            model_name='payrolltaxslabset',
            name='is_old_regime',
            field=models.BooleanField(
                default=False,
                help_text='If True, this slab set represents the old tax regime. Old regime allows additional deductions such as HRA, 80C, and 80D.',
            ),
        ),
    ]
