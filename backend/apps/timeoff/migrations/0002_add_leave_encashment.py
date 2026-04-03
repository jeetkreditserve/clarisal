from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('approvals', '0001_initial'),
        ('payroll', '0007_add_arrears'),
        ('timeoff', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='leavetype',
            name='allows_encashment',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='leavetype',
            name='max_encashment_days_per_year',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
        migrations.CreateModel(
            name='LeaveEncashmentRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('cycle_start', models.DateField()),
                ('cycle_end', models.DateField()),
                ('days_to_encash', models.DecimalField(decimal_places=2, max_digits=5)),
                ('encashment_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('status', models.CharField(choices=[('PENDING', 'Pending Approval'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('PAID', 'Paid'), ('CANCELLED', 'Cancelled')], default='PENDING', max_length=20)),
                ('rejection_reason', models.TextField(blank=True)),
                ('approval_run', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='leave_encashment_requests', to='approvals.approvalrun')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='leave_encashment_requests', to='employees.employee')),
                ('leave_type', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='encashment_requests', to='timeoff.leavetype')),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('paid_in_pay_run', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='leave_encashments', to='payroll.payrollrun')),
            ],
            options={
                'db_table': 'leave_encashment_requests',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='leaveencashmentrequest',
            index=models.Index(fields=['employee', 'status'], name='leave_encas_employee_4df4de_idx'),
        ),
        migrations.AddIndex(
            model_name='leaveencashmentrequest',
            index=models.Index(fields=['employee', 'cycle_start', 'cycle_end'], name='leave_encas_employee_a213b0_idx'),
        ),
    ]
