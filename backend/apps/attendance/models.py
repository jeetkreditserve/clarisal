from django.conf import settings
from django.db import models

from apps.common.models import AuditedBaseModel


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

