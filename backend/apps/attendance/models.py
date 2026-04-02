from datetime import time

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import AuditedBaseModel


class AttendanceDayStatus(models.TextChoices):
    PRESENT = 'PRESENT', 'Present'
    HALF_DAY = 'HALF_DAY', 'Half Day'
    ABSENT = 'ABSENT', 'Absent'
    INCOMPLETE = 'INCOMPLETE', 'Incomplete'
    HOLIDAY = 'HOLIDAY', 'Holiday'
    WEEK_OFF = 'WEEK_OFF', 'Week Off'
    ON_LEAVE = 'ON_LEAVE', 'On Leave'
    ON_DUTY = 'ON_DUTY', 'On Duty'


class AttendancePunchActionType(models.TextChoices):
    CHECK_IN = 'CHECK_IN', 'Check In'
    CHECK_OUT = 'CHECK_OUT', 'Check Out'
    RAW = 'RAW', 'Raw Punch'


class AttendancePunchSource(models.TextChoices):
    WEB = 'WEB', 'Web'
    IMPORT = 'IMPORT', 'Excel Import'
    API = 'API', 'External API'
    REGULARIZATION = 'REGULARIZATION', 'Regularization'
    MANUAL = 'MANUAL', 'Manual'


class AttendanceRegularizationStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Approval'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    CANCELLED = 'CANCELLED', 'Cancelled'
    WITHDRAWN = 'WITHDRAWN', 'Withdrawn'


class AttendanceSourceConfigKind(models.TextChoices):
    API = 'API', 'API Source'
    EXCEL = 'EXCEL', 'Excel Source'
    DEVICE = 'DEVICE', 'Device Source'


class AttendanceImportMode(models.TextChoices):
    ATTENDANCE_SHEET = 'ATTENDANCE_SHEET', 'Attendance Sheet'
    PUNCH_SHEET = 'PUNCH_SHEET', 'Punch Sheet'


class AttendanceImportStatus(models.TextChoices):
    FAILED = 'FAILED', 'Failed'
    READY_FOR_REVIEW = 'READY_FOR_REVIEW', 'Ready For Review'
    POSTED = 'POSTED', 'Posted'


class AttendanceImportRowStatus(models.TextChoices):
    VALID = 'VALID', 'Valid'
    ERROR = 'ERROR', 'Error'
    INCOMPLETE = 'INCOMPLETE', 'Incomplete'
    POSTED = 'POSTED', 'Posted'


class AttendanceRecordSource(models.TextChoices):
    EXCEL_IMPORT = 'EXCEL_IMPORT', 'Excel Import'
    MANUAL_OVERRIDE = 'MANUAL_OVERRIDE', 'Manual Override'
    REGULARIZATION = 'REGULARIZATION', 'Regularization'


class AttendancePolicy(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='attendance_policies',
    )
    name = models.CharField(max_length=255)
    timezone_name = models.CharField(max_length=64, default='Asia/Kolkata')
    default_start_time = models.TimeField(default=time(9, 0))
    default_end_time = models.TimeField(default=time(18, 0))
    grace_minutes = models.PositiveIntegerField(default=15)
    full_day_min_minutes = models.PositiveIntegerField(default=480)
    half_day_min_minutes = models.PositiveIntegerField(default=240)
    overtime_after_minutes = models.PositiveIntegerField(default=540)
    week_off_days = models.JSONField(default=list, blank=True)
    allow_web_punch = models.BooleanField(default=True)
    restrict_by_ip = models.BooleanField(default=False)
    allowed_ip_ranges = models.JSONField(default=list, blank=True)
    restrict_by_geo = models.BooleanField(default=False)
    allowed_geo_sites = models.JSONField(default=list, blank=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'attendance_policies'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['organisation'],
                condition=Q(is_default=True),
                name='unique_default_attendance_policy_per_org',
            ),
        ]

    def __str__(self):
        return f'{self.organisation.name} - {self.name}'


class Shift(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='attendance_shifts',
    )
    name = models.CharField(max_length=255)
    start_time = models.TimeField()
    end_time = models.TimeField()
    grace_minutes = models.PositiveIntegerField(null=True, blank=True)
    full_day_min_minutes = models.PositiveIntegerField(null=True, blank=True)
    half_day_min_minutes = models.PositiveIntegerField(null=True, blank=True)
    overtime_after_minutes = models.PositiveIntegerField(null=True, blank=True)
    is_overnight = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'attendance_shifts'
        ordering = ['name']

    def __str__(self):
        return f'{self.organisation.name} - {self.name}'


class ShiftAssignment(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='shift_assignments',
    )
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='shift_assignments',
    )
    shift = models.ForeignKey(
        Shift,
        on_delete=models.CASCADE,
        related_name='assignments',
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'attendance_shift_assignments'
        ordering = ['-start_date', 'employee__employee_code']
        indexes = [
            models.Index(fields=['organisation', 'employee', 'start_date']),
        ]

    def __str__(self):
        return f'{self.employee} - {self.shift.name}'


class AttendanceSourceConfig(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='attendance_source_configs',
    )
    name = models.CharField(max_length=255)
    kind = models.CharField(max_length=24, choices=AttendanceSourceConfigKind.choices)
    configuration = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    last_error = models.TextField(blank=True)

    class Meta:
        db_table = 'attendance_source_configs'
        ordering = ['name']

    def __str__(self):
        return f'{self.organisation.name} - {self.name}'


class AttendanceImportJob(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='attendance_import_jobs',
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='uploaded_attendance_import_jobs',
    )
    mode = models.CharField(max_length=32, choices=AttendanceImportMode.choices)
    status = models.CharField(max_length=24, choices=AttendanceImportStatus.choices)
    original_filename = models.CharField(max_length=255)
    total_rows = models.PositiveIntegerField(default=0)
    valid_rows = models.PositiveIntegerField(default=0)
    error_rows = models.PositiveIntegerField(default=0)
    posted_rows = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'attendance_import_jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organisation', 'mode', 'status']),
            models.Index(fields=['organisation', 'created_at']),
        ]

    def __str__(self):
        return f'{self.get_mode_display()} • {self.original_filename}'


class AttendanceImportRow(AuditedBaseModel):
    job = models.ForeignKey(
        AttendanceImportJob,
        on_delete=models.CASCADE,
        related_name='rows',
    )
    row_number = models.PositiveIntegerField()
    employee_code = models.CharField(max_length=20, blank=True)
    employee = models.ForeignKey(
        'employees.Employee',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    attendance_date = models.DateField(null=True, blank=True)
    check_in_at = models.DateTimeField(null=True, blank=True)
    check_out_at = models.DateTimeField(null=True, blank=True)
    raw_punch_times = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=16, choices=AttendanceImportRowStatus.choices)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'attendance_import_rows'
        ordering = ['row_number', 'created_at']
        indexes = [
            models.Index(fields=['job', 'status']),
            models.Index(fields=['employee', 'attendance_date']),
        ]

    def __str__(self):
        return f'{self.employee_code or "UNKNOWN"} • {self.attendance_date or "NA"}'


class AttendancePunch(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='attendance_punches',
    )
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='attendance_punches',
    )
    source_config = models.ForeignKey(
        AttendanceSourceConfig,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='punches',
    )
    import_job = models.ForeignKey(
        AttendanceImportJob,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='punches',
    )
    action_type = models.CharField(max_length=16, choices=AttendancePunchActionType.choices, default=AttendancePunchActionType.RAW)
    source = models.CharField(max_length=24, choices=AttendancePunchSource.choices, default=AttendancePunchSource.WEB)
    punch_at = models.DateTimeField()
    remote_ip = models.CharField(max_length=64, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'attendance_punches'
        ordering = ['-punch_at']
        indexes = [
            models.Index(fields=['organisation', 'punch_at']),
            models.Index(fields=['employee', 'punch_at']),
        ]

    def __str__(self):
        return f'{self.employee.employee_code} • {self.action_type} • {self.punch_at}'


class AttendanceRecord(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='attendance_records',
    )
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='attendance_records',
    )
    attendance_date = models.DateField()
    check_in_at = models.DateTimeField()
    check_out_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=24, choices=AttendanceRecordSource.choices, default=AttendanceRecordSource.EXCEL_IMPORT)
    import_job = models.ForeignKey(
        AttendanceImportJob,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='attendance_records',
    )

    class Meta:
        db_table = 'attendance_records'
        ordering = ['-attendance_date', 'employee__employee_code']
        constraints = [
            models.UniqueConstraint(
                fields=['organisation', 'employee', 'attendance_date'],
                name='unique_attendance_record_per_employee_day',
            ),
        ]
        indexes = [
            models.Index(fields=['organisation', 'attendance_date']),
            models.Index(fields=['employee', 'attendance_date']),
        ]

    def __str__(self):
        return f'{self.employee.employee_code} • {self.attendance_date}'


class AttendanceDay(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='attendance_days',
    )
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='attendance_days',
    )
    attendance_date = models.DateField()
    policy = models.ForeignKey(
        AttendancePolicy,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='attendance_days',
    )
    shift = models.ForeignKey(
        Shift,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='attendance_days',
    )
    status = models.CharField(max_length=24, choices=AttendanceDayStatus.choices, default=AttendanceDayStatus.ABSENT)
    source = models.CharField(max_length=24, choices=AttendancePunchSource.choices, blank=True, default='')
    check_in_at = models.DateTimeField(null=True, blank=True)
    check_out_at = models.DateTimeField(null=True, blank=True)
    worked_minutes = models.PositiveIntegerField(default=0)
    overtime_minutes = models.PositiveIntegerField(default=0)
    late_minutes = models.PositiveIntegerField(default=0)
    paid_fraction = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    leave_fraction = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    on_duty_fraction = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    is_holiday = models.BooleanField(default=False)
    is_week_off = models.BooleanField(default=False)
    is_late = models.BooleanField(default=False)
    needs_regularization = models.BooleanField(default=False)
    raw_punch_count = models.PositiveIntegerField(default=0)
    note = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'attendance_days'
        ordering = ['-attendance_date', 'employee__employee_code']
        constraints = [
            models.UniqueConstraint(
                fields=['organisation', 'employee', 'attendance_date'],
                name='unique_attendance_day_per_employee_date',
            ),
        ]
        indexes = [
            models.Index(fields=['organisation', 'attendance_date', 'status']),
            models.Index(fields=['employee', 'attendance_date']),
        ]

    def __str__(self):
        return f'{self.employee.employee_code} • {self.attendance_date} • {self.status}'


class AttendanceRegularizationRequest(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='attendance_regularization_requests',
    )
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='attendance_regularization_requests',
    )
    attendance_day = models.ForeignKey(
        AttendanceDay,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='regularization_requests',
    )
    attendance_date = models.DateField()
    requested_check_in_at = models.DateTimeField(null=True, blank=True)
    requested_check_out_at = models.DateTimeField(null=True, blank=True)
    reason = models.TextField()
    status = models.CharField(
        max_length=24,
        choices=AttendanceRegularizationStatus.choices,
        default=AttendanceRegularizationStatus.PENDING,
    )
    rejection_reason = models.TextField(blank=True)
    approval_run = models.ForeignKey(
        'approvals.ApprovalRun',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='attendance_regularization_requests',
    )

    class Meta:
        db_table = 'attendance_regularization_requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organisation', 'status']),
            models.Index(fields=['employee', 'attendance_date']),
        ]

    def __str__(self):
        return f'{self.employee.employee_code} • {self.attendance_date} • {self.status}'

    def handle_approval_status_change(self, new_status, rejection_reason=''):
        from .services import apply_regularization_status_change

        apply_regularization_status_change(self, new_status, rejection_reason=rejection_reason)
