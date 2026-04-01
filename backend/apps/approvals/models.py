import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class ApprovalRequestKind(models.TextChoices):
    LEAVE = 'LEAVE', 'Leave'
    ON_DUTY = 'ON_DUTY', 'On Duty'


class ApprovalStageMode(models.TextChoices):
    ALL = 'ALL', 'All approvers required'
    ANY = 'ANY', 'Any approver can complete'


class ApprovalApproverType(models.TextChoices):
    REPORTING_MANAGER = 'REPORTING_MANAGER', 'Reporting Manager'
    SPECIFIC_EMPLOYEE = 'SPECIFIC_EMPLOYEE', 'Specific Employee'
    PRIMARY_ORG_ADMIN = 'PRIMARY_ORG_ADMIN', 'Primary Organisation Admin'


class ApprovalFallbackType(models.TextChoices):
    NONE = 'NONE', 'None'
    SPECIFIC_EMPLOYEE = 'SPECIFIC_EMPLOYEE', 'Specific Employee'
    PRIMARY_ORG_ADMIN = 'PRIMARY_ORG_ADMIN', 'Primary Organisation Admin'


class ApprovalRunStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    CANCELLED = 'CANCELLED', 'Cancelled'


class ApprovalActionStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    SKIPPED = 'SKIPPED', 'Skipped'
    CANCELLED = 'CANCELLED', 'Cancelled'


class ApprovalWorkflow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='approval_workflows',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_approval_workflows',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'approval_workflows'
        ordering = ['name']

    def __str__(self):
        return f'{self.organisation.name} - {self.name}'


class ApprovalWorkflowRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.CASCADE,
        related_name='rules',
    )
    name = models.CharField(max_length=255)
    request_kind = models.CharField(max_length=20, choices=ApprovalRequestKind.choices)
    priority = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    department = models.ForeignKey(
        'departments.Department',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='approval_rules',
    )
    office_location = models.ForeignKey(
        'locations.OfficeLocation',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='approval_rules',
    )
    specific_employee = models.ForeignKey(
        'employees.Employee',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='approval_rules',
    )
    employment_type = models.CharField(max_length=20, blank=True)
    designation = models.CharField(max_length=255, blank=True)
    leave_type = models.ForeignKey(
        'timeoff.LeaveType',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='approval_rules',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'approval_workflow_rules'
        ordering = ['priority', 'created_at']

    def __str__(self):
        return f'{self.workflow.name} [{self.request_kind}]'


class ApprovalStage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.CASCADE,
        related_name='stages',
    )
    name = models.CharField(max_length=255)
    sequence = models.PositiveIntegerField()
    mode = models.CharField(max_length=10, choices=ApprovalStageMode.choices, default=ApprovalStageMode.ALL)
    fallback_type = models.CharField(
        max_length=24,
        choices=ApprovalFallbackType.choices,
        default=ApprovalFallbackType.NONE,
    )
    fallback_employee = models.ForeignKey(
        'employees.Employee',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='approval_stage_fallbacks',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'approval_stages'
        ordering = ['sequence', 'created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['workflow', 'sequence'],
                name='unique_stage_sequence_per_workflow',
            ),
        ]

    def __str__(self):
        return f'{self.workflow.name} - Stage {self.sequence}'


class ApprovalStageApprover(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stage = models.ForeignKey(
        ApprovalStage,
        on_delete=models.CASCADE,
        related_name='approvers',
    )
    approver_type = models.CharField(max_length=24, choices=ApprovalApproverType.choices)
    approver_employee = models.ForeignKey(
        'employees.Employee',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='stage_approver_assignments',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'approval_stage_approvers'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.stage} - {self.approver_type}'


class ApprovalRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='approval_runs',
    )
    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.PROTECT,
        related_name='runs',
    )
    request_kind = models.CharField(max_length=20, choices=ApprovalRequestKind.choices)
    requested_by = models.ForeignKey(
        'employees.Employee',
        on_delete=models.PROTECT,
        related_name='approval_runs',
    )
    status = models.CharField(max_length=20, choices=ApprovalRunStatus.choices, default=ApprovalRunStatus.PENDING)
    current_stage_sequence = models.PositiveIntegerField(default=1)
    subject_label = models.CharField(max_length=255)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'approval_runs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organisation', 'status']),
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f'{self.request_kind} - {self.subject_label}'


class ApprovalAction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    approval_run = models.ForeignKey(
        ApprovalRun,
        on_delete=models.CASCADE,
        related_name='actions',
    )
    stage = models.ForeignKey(
        ApprovalStage,
        on_delete=models.CASCADE,
        related_name='actions',
    )
    approver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='approval_actions',
    )
    approver_employee = models.ForeignKey(
        'employees.Employee',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_approval_actions',
    )
    status = models.CharField(
        max_length=20,
        choices=ApprovalActionStatus.choices,
        default=ApprovalActionStatus.PENDING,
    )
    comment = models.TextField(blank=True)
    acted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'approval_actions'
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['approval_run', 'stage', 'approver_user'],
                name='unique_approval_action_per_user_stage',
            ),
        ]
        indexes = [
            models.Index(fields=['approver_user', 'status']),
            models.Index(fields=['approval_run', 'status']),
        ]

    def __str__(self):
        return f'{self.approver_user.email} - {self.status}'
