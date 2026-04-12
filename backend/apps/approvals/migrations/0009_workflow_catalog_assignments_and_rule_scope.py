from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


def forwards(apps, schema_editor):
    Employee = apps.get_model('employees', 'Employee')
    Assignment = apps.get_model('approvals', 'ApprovalWorkflowAssignment')
    mapping = {
        'LEAVE': 'leave_approval_workflow_id',
        'ON_DUTY': 'on_duty_approval_workflow_id',
        'ATTENDANCE_REGULARIZATION': 'attendance_regularization_approval_workflow_id',
        'EXPENSE_CLAIM': 'expense_approval_workflow_id',
    }
    rows = []
    for employee in Employee.objects.all().only('id', 'organisation_id', *mapping.values()):
        for request_kind, field_name in mapping.items():
            workflow_id = getattr(employee, field_name)
            if workflow_id:
                rows.append(
                    Assignment(
                        organisation_id=employee.organisation_id,
                        employee_id=employee.id,
                        request_kind=request_kind,
                        workflow_id=workflow_id,
                        is_active=True,
                    )
                )
    Assignment.objects.bulk_create(rows, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ('approvals', '0008_alter_approvalrun_request_kind_and_more'),
        ('employees', '0012_manager_scope_indexes'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='approvalstage',
            name='fallback_type',
            field=models.CharField(
                choices=[
                    ('NONE', 'None'),
                    ('REPORTING_MANAGER', 'Reporting Manager'),
                    ('DEPARTMENT_HEAD', 'Department Head'),
                    ('ROLE', 'Role'),
                    ('SPECIFIC_EMPLOYEE', 'Specific Employee'),
                    ('PRIMARY_ORG_ADMIN', 'Primary Organisation Admin'),
                ],
                default='NONE',
                max_length=24,
            ),
        ),
        migrations.AlterField(
            model_name='approvalstageapprover',
            name='approver_type',
            field=models.CharField(
                choices=[
                    ('REPORTING_MANAGER', 'Reporting Manager'),
                    ('NTH_LEVEL_MANAGER', 'Nth Level Manager'),
                    ('DEPARTMENT_HEAD', 'Department Head'),
                    ('LOCATION_ADMIN', 'Location Admin'),
                    ('HR_BUSINESS_PARTNER', 'HR Business Partner'),
                    ('PAYROLL_ADMIN', 'Payroll Admin'),
                    ('FINANCE_APPROVER', 'Finance Approver'),
                    ('ROLE', 'Role'),
                    ('SPECIFIC_EMPLOYEE', 'Specific Employee'),
                    ('PRIMARY_ORG_ADMIN', 'Primary Organisation Admin'),
                ],
                max_length=24,
            ),
        ),
        migrations.AlterField(
            model_name='approvalstageescalationpolicy',
            name='escalation_target_type',
            field=models.CharField(
                choices=[
                    ('NONE', 'None'),
                    ('REPORTING_MANAGER', 'Reporting Manager'),
                    ('DEPARTMENT_HEAD', 'Department Head'),
                    ('ROLE', 'Role'),
                    ('SPECIFIC_EMPLOYEE', 'Specific Employee'),
                    ('PRIMARY_ORG_ADMIN', 'Primary Organisation Admin'),
                ],
                default='NONE',
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name='approvalstage',
            name='fallback_role_code',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='approvalstageapprover',
            name='manager_level',
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='approvalstageapprover',
            name='role_code',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='approvalstageescalationpolicy',
            name='escalation_role_code',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='approvalworkflowrule',
            name='band',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='approvalworkflowrule',
            name='cost_centre',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='approvalworkflowrule',
            name='grade',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='approvalworkflowrule',
            name='legal_entity',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='approvalworkflowrule',
            name='max_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True),
        ),
        migrations.AddField(
            model_name='approvalworkflowrule',
            name='min_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True),
        ),
        migrations.CreateModel(
            name='ApprovalWorkflowAssignment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('request_kind', models.CharField(choices=[('LEAVE', 'Leave'), ('ON_DUTY', 'On Duty'), ('ATTENDANCE_REGULARIZATION', 'Attendance Regularization'), ('EXPENSE_CLAIM', 'Expense Claim'), ('PAYROLL_PROCESSING', 'Payroll Processing'), ('SALARY_REVISION', 'Salary Revision'), ('COMPENSATION_TEMPLATE_CHANGE', 'Compensation Template Change'), ('PROMOTION', 'Promotion'), ('TRANSFER', 'Transfer')], max_length=32)),
                ('is_active', models.BooleanField(default=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='approval_workflow_assignments', to='employees.employee')),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='approval_workflow_assignments', to='organisations.organisation')),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='employee_assignments', to='approvals.approvalworkflow')),
            ],
            options={
                'db_table': 'approval_workflow_assignments',
                'ordering': ['request_kind', 'employee__employee_code', 'created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='approvalworkflowassignment',
            constraint=models.UniqueConstraint(condition=models.Q(('is_active', True)), fields=('organisation', 'employee', 'request_kind'), name='unique_active_approval_workflow_assignment'),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
