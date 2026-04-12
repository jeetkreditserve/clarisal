from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0011_employee_expense_approval_workflow'),
        ('recruitment', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='candidate',
            name='converted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='candidate',
            name='converted_to_employee',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='sourced_candidates',
                to='employees.employee',
            ),
        ),
    ]
