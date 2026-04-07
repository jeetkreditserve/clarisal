from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('payroll', '0015_rename_payroll_tds_organis_882124_idx_payroll_tds_organis_1f41a5_idx_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='compensationassignment',
            index=models.Index(
                fields=['employee', 'status', 'effective_from'],
                name='comp_assign_emp_status_eff_idx',
            ),
        ),
    ]
