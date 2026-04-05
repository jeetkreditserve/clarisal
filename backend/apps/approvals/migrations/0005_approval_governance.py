from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('approvals', '0004_payroll_request_kinds_and_requester_user'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ApprovalDelegation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('request_kinds', models.JSONField(default=list)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('delegate_employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='incoming_approval_delegations', to='employees.employee')),
                ('delegator_employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='outgoing_approval_delegations', to='employees.employee')),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='approval_delegations', to='organisations.organisation')),
            ],
            options={
                'db_table': 'approval_delegations',
                'ordering': ['-start_date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ApprovalStageEscalationPolicy',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('reminder_after_hours', models.PositiveIntegerField(blank=True, null=True)),
                ('escalate_after_hours', models.PositiveIntegerField(blank=True, null=True)),
                ('escalation_target_type', models.CharField(choices=[('NONE', 'None'), ('SPECIFIC_EMPLOYEE', 'Specific Employee'), ('PRIMARY_ORG_ADMIN', 'Primary Organisation Admin')], default='NONE', max_length=24)),
                ('is_active', models.BooleanField(default=True)),
                ('escalation_employee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approval_stage_escalation_policies', to='employees.employee')),
                ('stage', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='sla_policy', to='approvals.approvalstage')),
            ],
            options={
                'db_table': 'approval_stage_escalation_policies',
            },
        ),
        migrations.AddField(
            model_name='approvalaction',
            name='assignment_source',
            field=models.CharField(choices=[('DIRECT', 'Direct'), ('DELEGATED', 'Delegated'), ('ESCALATED', 'Escalated')], default='DIRECT', max_length=16),
        ),
        migrations.AddField(
            model_name='approvalaction',
            name='escalated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='approvalaction',
            name='escalated_from_action',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='escalated_actions', to='approvals.approvalaction'),
        ),
        migrations.AddField(
            model_name='approvalaction',
            name='original_approver_employee',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='original_assigned_approval_actions', to='employees.employee'),
        ),
        migrations.AddField(
            model_name='approvalaction',
            name='original_approver_user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='original_approval_actions', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='approvalaction',
            name='reminder_sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name='approvaldelegation',
            constraint=models.CheckConstraint(check=models.Q(('end_date__isnull', True), ('end_date__gte', models.F('start_date')), _connector='OR'), name='approval_delegation_end_date_after_start_date'),
        ),
        migrations.AddIndex(
            model_name='approvaldelegation',
            index=models.Index(fields=['organisation', 'is_active'], name='approval_de_organis_e47f0d_idx'),
        ),
        migrations.AddIndex(
            model_name='approvaldelegation',
            index=models.Index(fields=['delegator_employee', 'is_active'], name='approval_de_delegat_38ebbe_idx'),
        ),
    ]
