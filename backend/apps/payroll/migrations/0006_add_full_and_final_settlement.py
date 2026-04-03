from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('employees', '0003_employee_offboarding'),
        ('payroll', '0005_add_investment_declaration'),
    ]

    operations = [
        migrations.CreateModel(
            name='FullAndFinalSettlement',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('last_working_day', models.DateField()),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('CALCULATED', 'Calculated'), ('APPROVED', 'Approved'), ('PAID', 'Paid'), ('CANCELLED', 'Cancelled')], default='DRAFT', max_length=20)),
                ('prorated_salary', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('leave_encashment', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('gratuity', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('arrears', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('other_credits', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('tds_deduction', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('pf_deduction', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('loan_recovery', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('other_deductions', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('gross_payable', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('net_payable', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('notes', models.TextField(blank=True)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_fnf_settlements', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('employee', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='full_and_final_settlement', to='employees.employee')),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('offboarding_process', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='fnf_settlement', to='employees.employeeoffboardingprocess')),
            ],
            options={
                'db_table': 'full_and_final_settlements',
                'ordering': ['-created_at'],
            },
        ),
    ]
