from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('payroll', '0006_add_full_and_final_settlement'),
    ]

    operations = [
        migrations.CreateModel(
            name='Arrears',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('for_period_year', models.PositiveSmallIntegerField()),
                ('for_period_month', models.PositiveSmallIntegerField()),
                ('reason', models.CharField(max_length=200)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('is_included_in_payslip', models.BooleanField(default=False)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='arrears', to='employees.employee')),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('pay_run', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='arrears_items', to='payroll.payrollrun')),
            ],
            options={
                'db_table': 'payroll_arrears',
                'ordering': ['for_period_year', 'for_period_month', 'created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='arrears',
            index=models.Index(fields=['employee', 'pay_run'], name='payroll_arr_employee_d27c71_idx'),
        ),
    ]
