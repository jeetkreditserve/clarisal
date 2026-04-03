from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0007_add_arrears'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='payrollrunitem',
            index=models.Index(fields=['pay_run', 'employee'], name='payrunitem_run_emp_idx'),
        ),
        migrations.AddIndex(
            model_name='payrollrunitem',
            index=models.Index(fields=['employee', 'pay_run'], name='payrunitem_emp_run_idx'),
        ),
    ]
