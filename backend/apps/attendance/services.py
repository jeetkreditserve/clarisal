from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time
from io import BytesIO

from django.db import transaction
from django.utils import timezone
from openpyxl import Workbook, load_workbook

from apps.audit.services import log_audit_event
from apps.employees.models import Employee, EmployeeStatus

from .models import (
    AttendanceImportJob,
    AttendanceImportMode,
    AttendanceImportRow,
    AttendanceImportRowStatus,
    AttendanceImportStatus,
    AttendanceRecord,
    AttendanceRecordSource,
)

ATTENDANCE_HEADERS = ['employee_code', 'date', 'check_in', 'check_out']
PUNCH_HEADERS = ['employee_code', 'date', 'punch_time']
XLSX_CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def _normalize_header(value):
    return str(value or '').strip().lower().replace(' ', '_')


def _strip_string(value):
    return str(value or '').strip()


def _parse_date(value):
    if value is None or value == '':
        raise ValueError('Date is required.')
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = _strip_string(value)
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError('Date must be a valid Excel date or YYYY-MM-DD style value.')


def _parse_time_value(value, *, label):
    if value is None or value == '':
        raise ValueError(f'{label} is required.')
    if isinstance(value, datetime):
        return value.time().replace(tzinfo=None)
    if isinstance(value, time):
        return value.replace(tzinfo=None)
    text = _strip_string(value)
    for fmt in (
        '%H:%M',
        '%H:%M:%S',
        '%I:%M %p',
        '%I:%M:%S %p',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d %H:%M:%S',
        '%d-%m-%Y %H:%M',
        '%d-%m-%Y %H:%M:%S',
    ):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    raise ValueError(f'{label} must be a valid Excel time or time-like value.')


def _make_aware_datetime(attendance_date, time_value):
    naive = datetime.combine(attendance_date, time_value)
    return timezone.make_aware(naive, timezone.get_default_timezone())


def _load_sheet_rows(uploaded_file, expected_headers):
    workbook = load_workbook(uploaded_file, data_only=True)
    sheet = workbook[workbook.sheetnames[0]]
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        raise ValueError('The uploaded workbook is empty.')

    headers = [_normalize_header(value) for value in rows[0]]
    if headers[: len(expected_headers)] != expected_headers:
        raise ValueError(f'The workbook must contain these columns in order: {", ".join(expected_headers)}.')

    parsed_rows = []
    for row_number, row in enumerate(rows[1:], start=2):
        if not any(cell not in (None, '') for cell in row[: len(expected_headers)]):
            continue
        parsed_rows.append(
            {
                expected_headers[index]: row[index] if index < len(row) else None
                for index in range(len(expected_headers))
            }
            | {'row_number': row_number}
        )
    return parsed_rows


def _resolve_employee(organisation, employee_code):
    normalized_code = _strip_string(employee_code).upper()
    if not normalized_code:
        raise ValueError('Employee code is required.')
    employee = Employee.objects.filter(
        organisation=organisation,
        employee_code=normalized_code,
        status=EmployeeStatus.ACTIVE,
    ).select_related('user').first()
    if employee is None:
        raise ValueError('Employee code was not found in this organisation or is not active.')
    return normalized_code, employee


def _build_workbook_bytes(title, headers, rows, *, instructions=None, review_notes=None, validation_errors=None):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = title
    sheet.append(headers)
    for row in rows:
        sheet.append(row)

    if instructions:
        instructions_sheet = workbook.create_sheet('Instructions')
        instructions_sheet.append(['Instruction'])
        for item in instructions:
            instructions_sheet.append([item])

    if review_notes:
        notes_sheet = workbook.create_sheet('Review Notes')
        notes_sheet.append(['employee_code', 'date', 'punch_count', 'review_note'])
        for row in review_notes:
            notes_sheet.append(row)

    if validation_errors:
        errors_sheet = workbook.create_sheet('Validation Errors')
        errors_sheet.append(['row_number', 'employee_code', 'message'])
        for row in validation_errors:
            errors_sheet.append(row)

    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def build_attendance_sheet_sample():
    return _build_workbook_bytes(
        'Attendance Import',
        ATTENDANCE_HEADERS,
        [
            ['EMP100', '2026-04-01', '09:02', '18:11'],
            ['EMP101', '2026-04-01', '09:15', '18:07'],
        ],
        instructions=[
            'Use one row per employee per date.',
            'Required columns: employee_code, date, check_in, check_out.',
            'The file posts attendance directly after validation.',
            'Dates should be in YYYY-MM-DD or Excel date format.',
            'Times should be in HH:MM, HH:MM:SS, or Excel time format.',
        ],
    )


def build_punch_sheet_sample():
    return _build_workbook_bytes(
        'Punch Import',
        PUNCH_HEADERS,
        [
            ['EMP100', '2026-04-01', '09:02'],
            ['EMP100', '2026-04-01', '18:11'],
            ['EMP101', '2026-04-01', '09:15'],
        ],
        instructions=[
            'Use one row per punch.',
            'Required columns: employee_code, date, punch_time.',
            'The system converts each employee-day into one attendance row using first punch as check-in and last punch as check-out.',
            'Single-punch days are returned with a blank checkout for review.',
        ],
    )


def build_normalized_attendance_workbook(job):
    normalized_rows = []
    review_notes = []
    validation_errors = []
    for row in job.rows.order_by('row_number', 'created_at'):
        if row.status in {AttendanceImportRowStatus.VALID, AttendanceImportRowStatus.INCOMPLETE}:
            normalized_rows.append(
                [
                    row.employee_code,
                    row.attendance_date.isoformat() if row.attendance_date else '',
                    timezone.localtime(row.check_in_at).strftime('%H:%M') if row.check_in_at else '',
                    timezone.localtime(row.check_out_at).strftime('%H:%M') if row.check_out_at else '',
                ]
            )
            review_notes.append(
                [
                    row.employee_code,
                    row.attendance_date.isoformat() if row.attendance_date else '',
                    len(row.raw_punch_times),
                    row.error_message or 'Review generated attendance before re-uploading.',
                ]
            )
        elif row.status == AttendanceImportRowStatus.ERROR:
            validation_errors.append([row.row_number, row.employee_code, row.error_message])

    return _build_workbook_bytes(
        'Attendance Import',
        ATTENDANCE_HEADERS,
        normalized_rows,
        instructions=[
            'This file was generated from a raw punch upload.',
            'Review every row before re-uploading it through the attendance-sheet import.',
            'Blank checkout values must be corrected before posting attendance.',
        ],
        review_notes=review_notes,
        validation_errors=validation_errors,
    )


def _ensure_xlsx(uploaded_file):
    filename = getattr(uploaded_file, 'name', '')
    if not filename.lower().endswith('.xlsx'):
        raise ValueError('Only Excel .xlsx files are supported for attendance import.')


def import_attendance_sheet(*, organisation, uploaded_by, uploaded_file):
    _ensure_xlsx(uploaded_file)
    rows = _load_sheet_rows(uploaded_file, ATTENDANCE_HEADERS)
    if not rows:
        raise ValueError('The workbook does not contain any attendance rows.')

    with transaction.atomic():
        job = AttendanceImportJob.objects.create(
            organisation=organisation,
            uploaded_by=uploaded_by,
            mode=AttendanceImportMode.ATTENDANCE_SHEET,
            status=AttendanceImportStatus.FAILED,
            original_filename=getattr(uploaded_file, 'name', 'attendance.xlsx'),
            total_rows=len(rows),
        )

        seen_keys = set()
        valid_rows = []
        for row in rows:
            employee_code = _strip_string(row.get('employee_code')).upper()
            try:
                normalized_code, employee = _resolve_employee(organisation, employee_code)
                attendance_date = _parse_date(row.get('date'))
                check_in_at = _make_aware_datetime(attendance_date, _parse_time_value(row.get('check_in'), label='Check in'))
                check_out_at = _make_aware_datetime(attendance_date, _parse_time_value(row.get('check_out'), label='Check out'))
                if check_out_at < check_in_at:
                    raise ValueError('Check out cannot be earlier than check in.')
                dedupe_key = (employee.id, attendance_date)
                if dedupe_key in seen_keys:
                    raise ValueError('Only one attendance row per employee and date is allowed in the same upload.')
                seen_keys.add(dedupe_key)

                AttendanceImportRow.objects.create(
                    job=job,
                    row_number=row['row_number'],
                    employee_code=normalized_code,
                    employee=employee,
                    attendance_date=attendance_date,
                    check_in_at=check_in_at,
                    check_out_at=check_out_at,
                    status=AttendanceImportRowStatus.VALID,
                )
                valid_rows.append((employee, attendance_date, check_in_at, check_out_at))
            except ValueError as exc:
                AttendanceImportRow.objects.create(
                    job=job,
                    row_number=row['row_number'],
                    employee_code=employee_code,
                    status=AttendanceImportRowStatus.ERROR,
                    error_message=str(exc),
                )

        job.valid_rows = len(valid_rows)
        job.error_rows = job.rows.filter(status=AttendanceImportRowStatus.ERROR).count()
        if job.error_rows:
            job.status = AttendanceImportStatus.FAILED
            job.save(update_fields=['valid_rows', 'error_rows', 'status', 'modified_at'])
            log_audit_event(uploaded_by, 'attendance.import.failed', organisation=organisation, target=job, payload={'mode': job.mode})
            return job

        posted_rows = 0
        for employee, attendance_date, check_in_at, check_out_at in valid_rows:
            AttendanceRecord.objects.update_or_create(
                organisation=organisation,
                employee=employee,
                attendance_date=attendance_date,
                defaults={
                    'check_in_at': check_in_at,
                    'check_out_at': check_out_at,
                    'source': AttendanceRecordSource.EXCEL_IMPORT,
                    'import_job': job,
                },
            )
            posted_rows += 1

        job.rows.filter(status=AttendanceImportRowStatus.VALID).update(status=AttendanceImportRowStatus.POSTED)
        job.status = AttendanceImportStatus.POSTED
        job.posted_rows = posted_rows
        job.save(update_fields=['valid_rows', 'error_rows', 'status', 'posted_rows', 'modified_at'])
        log_audit_event(uploaded_by, 'attendance.import.posted', organisation=organisation, target=job, payload={'mode': job.mode, 'posted_rows': posted_rows})
        return job


def import_punch_sheet(*, organisation, uploaded_by, uploaded_file):
    _ensure_xlsx(uploaded_file)
    rows = _load_sheet_rows(uploaded_file, PUNCH_HEADERS)
    if not rows:
        raise ValueError('The workbook does not contain any punch rows.')

    with transaction.atomic():
        job = AttendanceImportJob.objects.create(
            organisation=organisation,
            uploaded_by=uploaded_by,
            mode=AttendanceImportMode.PUNCH_SHEET,
            status=AttendanceImportStatus.FAILED,
            original_filename=getattr(uploaded_file, 'name', 'attendance-punches.xlsx'),
            total_rows=len(rows),
        )
        grouped_punches = defaultdict(list)
        for row in rows:
            employee_code = _strip_string(row.get('employee_code')).upper()
            try:
                normalized_code, employee = _resolve_employee(organisation, employee_code)
                attendance_date = _parse_date(row.get('date'))
                punch_at = _make_aware_datetime(attendance_date, _parse_time_value(row.get('punch_time'), label='Punch time'))
                grouped_punches[(employee.id, attendance_date)].append((normalized_code, employee, punch_at, row['row_number']))
            except ValueError as exc:
                AttendanceImportRow.objects.create(
                    job=job,
                    row_number=row['row_number'],
                    employee_code=employee_code,
                    status=AttendanceImportRowStatus.ERROR,
                    error_message=str(exc),
                )

        generated_rows = 0
        for (_employee_id, attendance_date), punch_rows in sorted(grouped_punches.items(), key=lambda item: (item[0][1], item[0][0])):
            punch_rows.sort(key=lambda item: item[2])
            employee_code, employee = punch_rows[0][0], punch_rows[0][1]
            check_in_at = punch_rows[0][2]
            check_out_at = punch_rows[-1][2] if len(punch_rows) > 1 else None
            status_value = AttendanceImportRowStatus.VALID if check_out_at else AttendanceImportRowStatus.INCOMPLETE
            error_message = '' if check_out_at else 'Only one punch was found for this employee on this date. Add a checkout time before re-uploading.'
            AttendanceImportRow.objects.create(
                job=job,
                row_number=generated_rows + 2,
                employee_code=employee_code,
                employee=employee,
                attendance_date=attendance_date,
                check_in_at=check_in_at,
                check_out_at=check_out_at,
                raw_punch_times=[timezone.localtime(item[2]).strftime('%H:%M:%S') for item in punch_rows],
                status=status_value,
                error_message=error_message,
                metadata={'source_row_numbers': [item[3] for item in punch_rows], 'punch_count': len(punch_rows)},
            )
            generated_rows += 1

        job.valid_rows = generated_rows
        job.error_rows = job.rows.filter(status=AttendanceImportRowStatus.ERROR).count()
        job.status = AttendanceImportStatus.READY_FOR_REVIEW if generated_rows else AttendanceImportStatus.FAILED
        job.save(update_fields=['valid_rows', 'error_rows', 'status', 'modified_at'])
        log_audit_event(uploaded_by, 'attendance.import.normalized', organisation=organisation, target=job, payload={'mode': job.mode, 'generated_rows': generated_rows})
        return job

