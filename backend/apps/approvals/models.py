from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q

from apps.common.models import AuditedBaseModel


class ApprovalRequestKind(models.TextChoices):
    LEAVE = "LEAVE", "Leave"
    ON_DUTY = "ON_DUTY", "On Duty"
    ATTENDANCE_REGULARIZATION = "ATTENDANCE_REGULARIZATION", "Attendance Regularization"
    EXPENSE_CLAIM = "EXPENSE_CLAIM", "Expense Claim"
    PAYROLL_PROCESSING = "PAYROLL_PROCESSING", "Payroll Processing"
    SALARY_REVISION = "SALARY_REVISION", "Salary Revision"
    COMPENSATION_TEMPLATE_CHANGE = (
        "COMPENSATION_TEMPLATE_CHANGE",
        "Compensation Template Change",
    )
    PROMOTION = "PROMOTION", "Promotion"
    TRANSFER = "TRANSFER", "Transfer"


class ApprovalStageMode(models.TextChoices):
    ALL = "ALL", "All approvers required"
    ANY = "ANY", "Any approver can complete"


class ApprovalApproverType(models.TextChoices):
    REPORTING_MANAGER = "REPORTING_MANAGER", "Reporting Manager"
    NTH_LEVEL_MANAGER = "NTH_LEVEL_MANAGER", "Nth Level Manager"
    DEPARTMENT_HEAD = "DEPARTMENT_HEAD", "Department Head"
    LOCATION_ADMIN = "LOCATION_ADMIN", "Location Admin"
    HR_BUSINESS_PARTNER = "HR_BUSINESS_PARTNER", "HR Business Partner"
    PAYROLL_ADMIN = "PAYROLL_ADMIN", "Payroll Admin"
    FINANCE_APPROVER = "FINANCE_APPROVER", "Finance Approver"
    ROLE = "ROLE", "Role"
    SPECIFIC_EMPLOYEE = "SPECIFIC_EMPLOYEE", "Specific Employee"
    PRIMARY_ORG_ADMIN = "PRIMARY_ORG_ADMIN", "Primary Organisation Admin"


class ApprovalFallbackType(models.TextChoices):
    NONE = "NONE", "None"
    REPORTING_MANAGER = "REPORTING_MANAGER", "Reporting Manager"
    DEPARTMENT_HEAD = "DEPARTMENT_HEAD", "Department Head"
    ROLE = "ROLE", "Role"
    SPECIFIC_EMPLOYEE = "SPECIFIC_EMPLOYEE", "Specific Employee"
    PRIMARY_ORG_ADMIN = "PRIMARY_ORG_ADMIN", "Primary Organisation Admin"


class ApprovalRunStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"


class ApprovalActionStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    SKIPPED = "SKIPPED", "Skipped"
    CANCELLED = "CANCELLED", "Cancelled"


class ApprovalActionAssignmentSource(models.TextChoices):
    DIRECT = "DIRECT", "Direct"
    DELEGATED = "DELEGATED", "Delegated"
    ESCALATED = "ESCALATED", "Escalated"


class ApprovalWorkflow(AuditedBaseModel):
    organisation = models.ForeignKey(
        "organisations.Organisation",
        on_delete=models.CASCADE,
        related_name="approval_workflows",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    default_request_kind = models.CharField(
        max_length=32,
        choices=ApprovalRequestKind.choices,
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_approval_workflows",
    )

    class Meta:
        db_table = "approval_workflows"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "default_request_kind"],
                condition=Q(is_default=True) & Q(default_request_kind__isnull=False),
                name="unique_default_approval_workflow_per_request_kind",
            ),
        ]

    def __str__(self):
        return f"{self.organisation.name} - {self.name}"


class ApprovalWorkflowRule(AuditedBaseModel):
    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.CASCADE,
        related_name="rules",
    )
    name = models.CharField(max_length=255)
    request_kind = models.CharField(max_length=32, choices=ApprovalRequestKind.choices)
    priority = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    department = models.ForeignKey(
        "departments.Department",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="approval_rules",
    )
    office_location = models.ForeignKey(
        "locations.OfficeLocation",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="approval_rules",
    )
    specific_employee = models.ForeignKey(
        "employees.Employee",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="approval_rules",
    )
    employment_type = models.CharField(max_length=20, blank=True)
    designation = models.CharField(max_length=255, blank=True)
    leave_type = models.ForeignKey(
        "timeoff.LeaveType",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="approval_rules",
    )
    min_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    max_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    grade = models.CharField(max_length=120, blank=True)
    band = models.CharField(max_length=120, blank=True)
    cost_centre = models.CharField(max_length=120, blank=True)
    legal_entity = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = "approval_workflow_rules"
        ordering = ["priority", "created_at"]

    def __str__(self):
        return f"{self.workflow.name} [{self.request_kind}]"


class ApprovalWorkflowAssignment(AuditedBaseModel):
    organisation = models.ForeignKey(
        "organisations.Organisation",
        on_delete=models.CASCADE,
        related_name="approval_workflow_assignments",
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="approval_workflow_assignments",
    )
    request_kind = models.CharField(max_length=32, choices=ApprovalRequestKind.choices)
    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.CASCADE,
        related_name="employee_assignments",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "approval_workflow_assignments"
        ordering = ["request_kind", "employee__employee_code", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "employee", "request_kind"],
                condition=Q(is_active=True),
                name="unique_active_approval_workflow_assignment",
            ),
        ]

    def __str__(self):
        return f"{self.employee_id} {self.request_kind} -> {self.workflow_id}"


class ApprovalStage(AuditedBaseModel):
    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.CASCADE,
        related_name="stages",
    )
    name = models.CharField(max_length=255)
    sequence = models.PositiveIntegerField()
    mode = models.CharField(
        max_length=10, choices=ApprovalStageMode.choices, default=ApprovalStageMode.ALL
    )
    fallback_type = models.CharField(
        max_length=24,
        choices=ApprovalFallbackType.choices,
        default=ApprovalFallbackType.NONE,
    )
    fallback_employee = models.ForeignKey(
        "employees.Employee",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approval_stage_fallbacks",
    )
    fallback_role_code = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = "approval_stages"
        ordering = ["sequence", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "sequence"],
                name="unique_stage_sequence_per_workflow",
            ),
        ]

    def __str__(self):
        return f"{self.workflow.name} - Stage {self.sequence}"


class ApprovalStageEscalationPolicy(AuditedBaseModel):
    stage = models.OneToOneField(
        ApprovalStage,
        on_delete=models.CASCADE,
        related_name="sla_policy",
    )
    reminder_after_hours = models.PositiveIntegerField(null=True, blank=True)
    escalate_after_hours = models.PositiveIntegerField(null=True, blank=True)
    escalation_target_type = models.CharField(
        max_length=24,
        choices=ApprovalFallbackType.choices,
        default=ApprovalFallbackType.NONE,
    )
    escalation_employee = models.ForeignKey(
        "employees.Employee",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approval_stage_escalation_policies",
    )
    escalation_role_code = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "approval_stage_escalation_policies"

    def __str__(self):
        return f"SLA policy for {self.stage}"


class ApprovalStageApprover(AuditedBaseModel):
    stage = models.ForeignKey(
        ApprovalStage,
        on_delete=models.CASCADE,
        related_name="approvers",
    )
    approver_type = models.CharField(
        max_length=24, choices=ApprovalApproverType.choices
    )
    approver_employee = models.ForeignKey(
        "employees.Employee",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="stage_approver_assignments",
    )
    manager_level = models.PositiveSmallIntegerField(default=1)
    role_code = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = "approval_stage_approvers"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.stage} - {self.approver_type}"


class ApprovalRun(AuditedBaseModel):
    organisation = models.ForeignKey(
        "organisations.Organisation",
        on_delete=models.CASCADE,
        related_name="approval_runs",
    )
    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.PROTECT,
        related_name="runs",
    )
    request_kind = models.CharField(max_length=32, choices=ApprovalRequestKind.choices)
    requested_by = models.ForeignKey(
        "employees.Employee",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="approval_runs",
    )
    requested_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="requested_approval_runs",
    )
    status = models.CharField(
        max_length=20,
        choices=ApprovalRunStatus.choices,
        default=ApprovalRunStatus.PENDING,
    )
    current_stage_sequence = models.PositiveIntegerField(default=1)
    subject_label = models.CharField(max_length=255)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        db_table = "approval_runs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organisation", "status"]),
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return f"{self.request_kind} - {self.subject_label}"

    @property
    def requester_name(self):
        if self.requested_by_user:
            return self.requested_by_user.full_name
        if self.requested_by:
            return self.requested_by.user.full_name
        return ""


class ApprovalAction(AuditedBaseModel):
    approval_run = models.ForeignKey(
        ApprovalRun,
        on_delete=models.CASCADE,
        related_name="actions",
    )
    stage = models.ForeignKey(
        ApprovalStage,
        on_delete=models.CASCADE,
        related_name="actions",
    )
    approver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="approval_actions",
    )
    approver_employee = models.ForeignKey(
        "employees.Employee",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_approval_actions",
    )
    assignment_source = models.CharField(
        max_length=16,
        choices=ApprovalActionAssignmentSource.choices,
        default=ApprovalActionAssignmentSource.DIRECT,
    )
    original_approver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="original_approval_actions",
    )
    original_approver_employee = models.ForeignKey(
        "employees.Employee",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="original_assigned_approval_actions",
    )
    status = models.CharField(
        max_length=20,
        choices=ApprovalActionStatus.choices,
        default=ApprovalActionStatus.PENDING,
    )
    comment = models.TextField(blank=True)
    acted_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    escalated_from_action = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="escalated_actions",
    )

    class Meta:
        db_table = "approval_actions"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["approval_run", "stage", "approver_user"],
                name="unique_approval_action_per_user_stage",
            ),
        ]
        indexes = [
            models.Index(fields=["approver_user", "status"]),
            models.Index(fields=["approval_run", "status"]),
        ]

    def __str__(self):
        return f"{self.approver_user.email} - {self.status}"


class ApprovalDelegation(AuditedBaseModel):
    organisation = models.ForeignKey(
        "organisations.Organisation",
        on_delete=models.CASCADE,
        related_name="approval_delegations",
    )
    delegator_employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="outgoing_approval_delegations",
    )
    delegate_employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="incoming_approval_delegations",
    )
    request_kinds = models.JSONField(default=list)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "approval_delegations"
        ordering = ["-start_date", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__isnull=True)
                | Q(end_date__gte=models.F("start_date")),
                name="approval_delegation_end_date_after_start_date",
            ),
        ]
        indexes = [
            models.Index(fields=["organisation", "is_active"]),
            models.Index(fields=["delegator_employee", "is_active"]),
        ]

    def __str__(self):
        return f"{self.delegator_employee_id} -> {self.delegate_employee_id}"
