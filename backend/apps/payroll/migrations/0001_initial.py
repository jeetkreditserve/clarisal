from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('approvals', '0004_payroll_request_kinds_and_requester_user'),
        ('employees', '0002_employee_approval_workflows'),
        ('organisations', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompensationTemplate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('PENDING_APPROVAL', 'Pending Approval'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], default='DRAFT', max_length=24)),
                ('approval_run', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='compensation_templates', to='approvals.approvalrun')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='compensation_templates', to='organisations.organisation')),
            ],
            options={
                'db_table': 'compensation_templates',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='PayrollRun',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('period_year', models.PositiveIntegerField()),
                ('period_month', models.PositiveIntegerField()),
                ('run_type', models.CharField(choices=[('REGULAR', 'Regular'), ('RERUN', 'Rerun')], default='REGULAR', max_length=16)),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('CALCULATED', 'Calculated'), ('APPROVAL_PENDING', 'Approval Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('FINALIZED', 'Finalized'), ('CANCELLED', 'Cancelled')], default='DRAFT', max_length=24)),
                ('calculated_at', models.DateTimeField(blank=True, null=True)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('finalized_at', models.DateTimeField(blank=True, null=True)),
                ('approval_run', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payroll_runs', to='approvals.approvalrun')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payroll_runs', to='organisations.organisation')),
                ('source_run', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reruns', to='payroll.payrollrun')),
            ],
            options={
                'db_table': 'payroll_runs',
                'ordering': ['-period_year', '-period_month', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PayrollTaxSlabSet',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('country_code', models.CharField(default='IN', max_length=2)),
                ('fiscal_year', models.CharField(max_length=16)),
                ('is_active', models.BooleanField(default=True)),
                ('is_system_master', models.BooleanField(default=False)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('organisation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='payroll_tax_slab_sets', to='organisations.organisation')),
                ('source_set', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='derived_sets', to='payroll.payrolltaxslabset')),
            ],
            options={
                'db_table': 'payroll_tax_slab_sets',
                'ordering': ['organisation_id', 'fiscal_year', 'name'],
            },
        ),
        migrations.CreateModel(
            name='PayrollComponent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('code', models.CharField(max_length=32)),
                ('name', models.CharField(max_length=255)),
                ('component_type', models.CharField(choices=[('EARNING', 'Earning'), ('EMPLOYEE_DEDUCTION', 'Employee Deduction'), ('EMPLOYER_CONTRIBUTION', 'Employer Contribution'), ('REIMBURSEMENT', 'Reimbursement')], max_length=32)),
                ('is_taxable', models.BooleanField(default=True)),
                ('is_system_default', models.BooleanField(default=False)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payroll_components', to='organisations.organisation')),
            ],
            options={
                'db_table': 'payroll_components',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='PayrollTaxSlab',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('min_income', models.DecimalField(decimal_places=2, max_digits=12)),
                ('max_income', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('rate_percent', models.DecimalField(decimal_places=2, max_digits=5)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('slab_set', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='slabs', to='payroll.payrolltaxslabset')),
            ],
            options={
                'db_table': 'payroll_tax_slabs',
                'ordering': ['min_income', 'created_at'],
            },
        ),
        migrations.CreateModel(
            name='PayrollRunItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(choices=[('READY', 'Ready'), ('EXCEPTION', 'Exception')], default='READY', max_length=16)),
                ('gross_pay', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('employee_deductions', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('employer_contributions', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('income_tax', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('total_deductions', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('net_pay', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('snapshot', models.JSONField(blank=True, default=dict)),
                ('message', models.TextField(blank=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payroll_run_items', to='employees.employee')),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('pay_run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='payroll.payrollrun')),
            ],
            options={
                'db_table': 'payroll_run_items',
                'ordering': ['employee__employee_code', 'created_at'],
            },
        ),
        migrations.CreateModel(
            name='Payslip',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('slip_number', models.CharField(max_length=64)),
                ('period_year', models.PositiveIntegerField()),
                ('period_month', models.PositiveIntegerField()),
                ('snapshot', models.JSONField(blank=True, default=dict)),
                ('rendered_text', models.TextField(blank=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payslips', to='employees.employee')),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payslips', to='organisations.organisation')),
                ('pay_run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payslips', to='payroll.payrollrun')),
                ('pay_run_item', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='payslip', to='payroll.payrollrunitem')),
            ],
            options={
                'db_table': 'payslips',
                'ordering': ['-period_year', '-period_month', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CompensationTemplateLine',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('monthly_amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('sequence', models.PositiveIntegerField(default=1)),
                ('component', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='template_lines', to='payroll.payrollcomponent')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='payroll.compensationtemplate')),
            ],
            options={
                'db_table': 'compensation_template_lines',
                'ordering': ['sequence', 'created_at'],
            },
        ),
        migrations.CreateModel(
            name='CompensationAssignment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('effective_from', models.DateField()),
                ('version', models.PositiveIntegerField(default=1)),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('PENDING_APPROVAL', 'Pending Approval'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], default='DRAFT', max_length=24)),
                ('approval_run', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='compensation_assignments', to='approvals.approvalrun')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='compensation_assignments', to='employees.employee')),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='assignments', to='payroll.compensationtemplate')),
            ],
            options={
                'db_table': 'compensation_assignments',
                'ordering': ['-effective_from', '-version', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CompensationAssignmentLine',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('component_name', models.CharField(max_length=255)),
                ('component_type', models.CharField(choices=[('EARNING', 'Earning'), ('EMPLOYEE_DEDUCTION', 'Employee Deduction'), ('EMPLOYER_CONTRIBUTION', 'Employer Contribution'), ('REIMBURSEMENT', 'Reimbursement')], max_length=32)),
                ('monthly_amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('is_taxable', models.BooleanField(default=True)),
                ('sequence', models.PositiveIntegerField(default=1)),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='payroll.compensationassignment')),
                ('component', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='assignment_lines', to='payroll.payrollcomponent')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'compensation_assignment_lines',
                'ordering': ['sequence', 'created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='compensationtemplate',
            constraint=models.UniqueConstraint(fields=('organisation', 'name'), name='unique_compensation_template_name_per_org'),
        ),
        migrations.AddConstraint(
            model_name='payrolltaxslabset',
            constraint=models.UniqueConstraint(condition=models.Q(organisation__isnull=False), fields=('organisation', 'name', 'fiscal_year'), name='unique_payroll_tax_slab_set_per_org_and_year'),
        ),
        migrations.AddConstraint(
            model_name='payrollcomponent',
            constraint=models.UniqueConstraint(fields=('organisation', 'code'), name='unique_payroll_component_code_per_org'),
        ),
        migrations.AddConstraint(
            model_name='payrollrunitem',
            constraint=models.UniqueConstraint(fields=('pay_run', 'employee'), name='unique_payroll_run_item_per_employee'),
        ),
        migrations.AddConstraint(
            model_name='payslip',
            constraint=models.UniqueConstraint(fields=('employee', 'pay_run'), name='unique_payslip_per_employee_per_run'),
        ),
    ]
