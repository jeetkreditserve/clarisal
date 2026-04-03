from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import AuditedBaseModel


class DaySession(models.TextChoices):
    FULL_DAY = 'FULL_DAY', 'Full Day'
    FIRST_HALF = 'FIRST_HALF', 'First Half'
    SECOND_HALF = 'SECOND_HALF', 'Second Half'


class HolidayCalendarStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    PUBLISHED = 'PUBLISHED', 'Published'
    ARCHIVED = 'ARCHIVED', 'Archived'


class HolidayClassification(models.TextChoices):
    PUBLIC = 'PUBLIC', 'Public Holiday'
    RESTRICTED = 'RESTRICTED', 'Restricted Holiday'
    COMPANY = 'COMPANY', 'Company Holiday'


class LeaveCycleType(models.TextChoices):
    CALENDAR_YEAR = 'CALENDAR_YEAR', 'Calendar Year'
    FINANCIAL_YEAR = 'FINANCIAL_YEAR', 'Financial Year'
    CUSTOM_FIXED_START = 'CUSTOM_FIXED_START', 'Custom Fixed Start'
    EMPLOYEE_JOINING_DATE = 'EMPLOYEE_JOINING_DATE', 'Employee Joining Date'


class LeaveCreditFrequency(models.TextChoices):
    MANUAL = 'MANUAL', 'Manual'
    MONTHLY = 'MONTHLY', 'Monthly'
    QUARTERLY = 'QUARTERLY', 'Quarterly'
    HALF_YEARLY = 'HALF_YEARLY', 'Half Yearly'
    YEARLY = 'YEARLY', 'Yearly'


class CarryForwardMode(models.TextChoices):
    NONE = 'NONE', 'None'
    CAPPED = 'CAPPED', 'Capped'
    UNLIMITED = 'UNLIMITED', 'Unlimited'


class LeaveBalanceEntryType(models.TextChoices):
    OPENING = 'OPENING', 'Opening'
    CREDIT = 'CREDIT', 'Credit'
    ADJUSTMENT = 'ADJUSTMENT', 'Adjustment'
    DEBIT = 'DEBIT', 'Debit'
    CARRY_FORWARD = 'CARRY_FORWARD', 'Carry Forward'
    EXPIRY = 'EXPIRY', 'Expiry'


class LeaveRequestStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Approval'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    CANCELLED = 'CANCELLED', 'Cancelled'
    WITHDRAWN = 'WITHDRAWN', 'Withdrawn'


class OnDutyRequestStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Approval'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    CANCELLED = 'CANCELLED', 'Cancelled'
    WITHDRAWN = 'WITHDRAWN', 'Withdrawn'


class LeaveEncashmentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Approval'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    PAID = 'PAID', 'Paid'
    CANCELLED = 'CANCELLED', 'Cancelled'


class OnDutyDurationType(models.TextChoices):
    FULL_DAY = 'FULL_DAY', 'Full Day'
    FIRST_HALF = 'FIRST_HALF', 'First Half'
    SECOND_HALF = 'SECOND_HALF', 'Second Half'
    TIME_RANGE = 'TIME_RANGE', 'Time Range'


class HolidayCalendar(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='holiday_calendars',
    )
    name = models.CharField(max_length=255)
    year = models.PositiveIntegerField()
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=HolidayCalendarStatus.choices, default=HolidayCalendarStatus.DRAFT)
    is_default = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_holiday_calendars',
    )
    published_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        db_table = 'holiday_calendars'
        ordering = ['-year', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['organisation', 'year'],
                condition=Q(is_default=True),
                name='unique_default_holiday_calendar_per_year',
            ),
        ]

    def __str__(self):
        return f'{self.organisation.name} {self.year} - {self.name}'


class HolidayCalendarLocation(AuditedBaseModel):
    holiday_calendar = models.ForeignKey(
        HolidayCalendar,
        on_delete=models.CASCADE,
        related_name='location_assignments',
    )
    office_location = models.ForeignKey(
        'locations.OfficeLocation',
        on_delete=models.CASCADE,
        related_name='holiday_calendar_assignments',
    )
    class Meta:
        db_table = 'holiday_calendar_locations'
        constraints = [
            models.UniqueConstraint(
                fields=['holiday_calendar', 'office_location'],
                name='unique_holiday_calendar_location_assignment',
            ),
        ]


class Holiday(AuditedBaseModel):
    holiday_calendar = models.ForeignKey(
        HolidayCalendar,
        on_delete=models.CASCADE,
        related_name='holidays',
    )
    name = models.CharField(max_length=255)
    holiday_date = models.DateField()
    classification = models.CharField(max_length=20, choices=HolidayClassification.choices, default=HolidayClassification.PUBLIC)
    session = models.CharField(max_length=20, choices=DaySession.choices, default=DaySession.FULL_DAY)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'holidays'
        ordering = ['holiday_date', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['holiday_calendar', 'holiday_date', 'name'],
                name='unique_holiday_per_calendar_date_name',
            ),
        ]


class LeaveCycle(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='leave_cycles',
    )
    name = models.CharField(max_length=255)
    cycle_type = models.CharField(max_length=32, choices=LeaveCycleType.choices, default=LeaveCycleType.CALENDAR_YEAR)
    start_month = models.PositiveSmallIntegerField(default=1)
    start_day = models.PositiveSmallIntegerField(default=1)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_leave_cycles',
    )
    class Meta:
        db_table = 'leave_cycles'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['organisation'],
                condition=Q(is_default=True),
                name='unique_default_leave_cycle_per_org',
            ),
        ]

    def __str__(self):
        return f'{self.organisation.name} - {self.name}'


class LeavePlan(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='leave_plans',
    )
    leave_cycle = models.ForeignKey(
        LeaveCycle,
        on_delete=models.PROTECT,
        related_name='leave_plans',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    priority = models.PositiveIntegerField(default=100)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_leave_plans',
    )
    class Meta:
        db_table = 'leave_plans'
        ordering = ['priority', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['organisation'],
                condition=Q(is_default=True),
                name='unique_default_leave_plan_per_org',
            ),
        ]

    def __str__(self):
        return f'{self.organisation.name} - {self.name}'


class LeavePlanRule(AuditedBaseModel):
    leave_plan = models.ForeignKey(
        LeavePlan,
        on_delete=models.CASCADE,
        related_name='rules',
    )
    name = models.CharField(max_length=255)
    priority = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    department = models.ForeignKey(
        'departments.Department',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='leave_plan_rules',
    )
    office_location = models.ForeignKey(
        'locations.OfficeLocation',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='leave_plan_rules',
    )
    specific_employee = models.ForeignKey(
        'employees.Employee',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='leave_plan_rules',
    )
    employment_type = models.CharField(max_length=20, blank=True)
    designation = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'leave_plan_rules'
        ordering = ['priority', 'created_at']


class LeavePlanEmployeeAssignment(AuditedBaseModel):
    leave_plan = models.ForeignKey(
        LeavePlan,
        on_delete=models.CASCADE,
        related_name='employee_assignments',
    )
    employee = models.OneToOneField(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='leave_plan_assignment',
    )
    class Meta:
        db_table = 'leave_plan_employee_assignments'


class LeaveType(AuditedBaseModel):
    leave_plan = models.ForeignKey(
        LeavePlan,
        on_delete=models.CASCADE,
        related_name='leave_types',
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=20, default='#2563eb')
    is_paid = models.BooleanField(default=True)
    is_loss_of_pay = models.BooleanField(default=False)
    annual_entitlement = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    credit_frequency = models.CharField(max_length=20, choices=LeaveCreditFrequency.choices, default=LeaveCreditFrequency.YEARLY)
    credit_day_of_period = models.PositiveSmallIntegerField(null=True, blank=True)
    prorate_on_join = models.BooleanField(default=True)
    carry_forward_mode = models.CharField(max_length=20, choices=CarryForwardMode.choices, default=CarryForwardMode.NONE)
    carry_forward_cap = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    max_balance = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    allows_encashment = models.BooleanField(default=False)
    max_encashment_days_per_year = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    allows_half_day = models.BooleanField(default=True)
    requires_attachment = models.BooleanField(default=False)
    attachment_after_days = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    min_notice_days = models.PositiveIntegerField(default=0)
    max_consecutive_days = models.PositiveIntegerField(null=True, blank=True)
    allow_past_request = models.BooleanField(default=False)
    allow_future_request = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'leave_types'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['leave_plan', 'code'],
                name='unique_leave_type_code_per_plan',
            ),
        ]

    def __str__(self):
        return f'{self.leave_plan.name} - {self.name}'


class LeaveBalance(AuditedBaseModel):
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='leave_balances',
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name='balances',
    )
    cycle_start = models.DateField()
    cycle_end = models.DateField()
    opening_balance = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    credited_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    used_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    pending_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    carried_forward_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    class Meta:
        db_table = 'leave_balances'
        ordering = ['leave_type__name']
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'leave_type', 'cycle_start', 'cycle_end'],
                name='unique_leave_balance_per_employee_cycle',
            ),
        ]


class LeaveBalanceLedgerEntry(AuditedBaseModel):
    leave_balance = models.ForeignKey(
        LeaveBalance,
        on_delete=models.CASCADE,
        related_name='ledger_entries',
    )
    entry_type = models.CharField(max_length=20, choices=LeaveBalanceEntryType.choices)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    effective_date = models.DateField()
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='leave_balance_entries',
    )
    class Meta:
        db_table = 'leave_balance_ledger_entries'
        ordering = ['-effective_date', '-created_at']


class LeaveRequest(AuditedBaseModel):
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='leave_requests',
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name='leave_requests',
    )
    start_date = models.DateField()
    end_date = models.DateField()
    start_session = models.CharField(max_length=20, choices=DaySession.choices, default=DaySession.FULL_DAY)
    end_session = models.CharField(max_length=20, choices=DaySession.choices, default=DaySession.FULL_DAY)
    total_units = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=LeaveRequestStatus.choices, default=LeaveRequestStatus.PENDING)
    rejection_reason = models.TextField(blank=True)
    attachment_file_key = models.CharField(max_length=500, blank=True)
    attachment_file_name = models.CharField(max_length=255, blank=True)
    attachment_mime_type = models.CharField(max_length=100, blank=True)
    attachment_file_size = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'leave_requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['employee', 'start_date', 'end_date']),
            # Composite index for leave balance aggregate queries
            models.Index(fields=['employee', 'leave_type', 'status', 'start_date'], name='leave_req_balance_idx'),
        ]


class OnDutyPolicy(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='on_duty_policies',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    allow_half_day = models.BooleanField(default=True)
    allow_time_range = models.BooleanField(default=True)
    requires_attachment = models.BooleanField(default=False)
    min_notice_days = models.PositiveIntegerField(default=0)
    allow_past_request = models.BooleanField(default=False)
    allow_future_request = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_on_duty_policies',
    )
    class Meta:
        db_table = 'on_duty_policies'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['organisation'],
                condition=Q(is_default=True),
                name='unique_default_on_duty_policy_per_org',
            ),
        ]


class OnDutyRequest(AuditedBaseModel):
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='on_duty_requests',
    )
    policy = models.ForeignKey(
        OnDutyPolicy,
        on_delete=models.PROTECT,
        related_name='requests',
    )
    start_date = models.DateField()
    end_date = models.DateField()
    duration_type = models.CharField(max_length=20, choices=OnDutyDurationType.choices, default=OnDutyDurationType.FULL_DAY)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    total_units = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    purpose = models.TextField()
    destination = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=OnDutyRequestStatus.choices, default=OnDutyRequestStatus.PENDING)
    rejection_reason = models.TextField(blank=True)
    attachment_file_key = models.CharField(max_length=500, blank=True)
    attachment_file_name = models.CharField(max_length=255, blank=True)
    attachment_mime_type = models.CharField(max_length=100, blank=True)
    attachment_file_size = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'on_duty_requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['employee', 'start_date', 'end_date']),
        ]


class LeaveEncashmentRequest(AuditedBaseModel):
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='leave_encashment_requests',
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name='encashment_requests',
    )
    cycle_start = models.DateField()
    cycle_end = models.DateField()
    days_to_encash = models.DecimalField(max_digits=5, decimal_places=2)
    encashment_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=LeaveEncashmentStatus.choices, default=LeaveEncashmentStatus.PENDING)
    approval_run = models.ForeignKey(
        'approvals.ApprovalRun',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='leave_encashment_requests',
    )
    rejection_reason = models.TextField(blank=True)
    paid_in_pay_run = models.ForeignKey(
        'payroll.PayrollRun',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='leave_encashments',
    )

    class Meta:
        db_table = 'leave_encashment_requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['employee', 'cycle_start', 'cycle_end']),
        ]

    def handle_approval_status_change(self, new_status: str, rejection_reason=''):
        if new_status == LeaveEncashmentStatus.APPROVED:
            from apps.timeoff.services import finalize_leave_encashment

            finalize_leave_encashment(self)
