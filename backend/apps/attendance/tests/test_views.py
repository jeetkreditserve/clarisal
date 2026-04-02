from datetime import date
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import Workbook, load_workbook
from rest_framework.test import APIClient

from apps.accounts.models import AccountType, User, UserRole
from apps.attendance.models import AttendanceImportStatus, AttendanceRecord
from apps.employees.models import Employee, EmployeeStatus
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationStatus,
)


def build_xlsx(headers, rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


@pytest.fixture
def attendance_setup(db):
    organisation = Organisation.objects.create(
        name='Acme Attendance',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    org_admin_user = User.objects.create_user(
        email='attendance-admin@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.ORG_ADMIN,
        organisation=organisation,
        is_active=True,
    )
    OrganisationMembership.objects.create(
        user=org_admin_user,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
    )
    employee_user = User.objects.create_user(
        email='attendance-employee@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        organisation=organisation,
        is_active=True,
    )
    employee = Employee.objects.create(
        organisation=organisation,
        user=employee_user,
        employee_code='EMP100',
        designation='Engineer',
        status=EmployeeStatus.ACTIVE,
        date_of_joining=date(2026, 4, 1),
    )

    client = APIClient()
    client.force_authenticate(user=org_admin_user)
    session = client.session
    session['active_workspace_kind'] = 'ADMIN'
    session['active_admin_org_id'] = str(organisation.id)
    session.save()

    return {
        'organisation': organisation,
        'org_admin_user': org_admin_user,
        'employee': employee,
        'client': client,
    }


@pytest.mark.django_db
class TestAttendanceImportViews:
    def test_sample_template_downloads_return_xlsx_files(self, attendance_setup):
        client = attendance_setup['client']

        attendance_response = client.get('/api/org/attendance/imports/templates/attendance-sheet/')
        punch_response = client.get('/api/org/attendance/imports/templates/punch-sheet/')

        assert attendance_response.status_code == 200
        assert punch_response.status_code == 200
        assert attendance_response['Content-Type'].startswith('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        assert punch_response['Content-Type'].startswith('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        attendance_workbook = load_workbook(BytesIO(attendance_response.content))
        punch_workbook = load_workbook(BytesIO(punch_response.content))

        assert [attendance_workbook.active['A1'].value, attendance_workbook.active['B1'].value, attendance_workbook.active['C1'].value, attendance_workbook.active['D1'].value] == ['employee_code', 'date', 'check_in', 'check_out']
        assert [punch_workbook.active['A1'].value, punch_workbook.active['B1'].value, punch_workbook.active['C1'].value] == ['employee_code', 'date', 'punch_time']

    def test_attendance_sheet_import_posts_attendance_records(self, attendance_setup):
        client = attendance_setup['client']
        employee = attendance_setup['employee']
        workbook_bytes = build_xlsx(
            ['employee_code', 'date', 'check_in', 'check_out'],
            [['EMP100', '2026-04-02', '09:05', '18:12']],
        )

        response = client.post(
            '/api/org/attendance/imports/attendance-sheet/',
            {'file': SimpleUploadedFile('attendance.xlsx', workbook_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},
        )

        assert response.status_code == 201
        assert response.data['status'] == AttendanceImportStatus.POSTED
        assert response.data['posted_rows'] == 1

        record = AttendanceRecord.objects.get(employee=employee, attendance_date=date(2026, 4, 2))
        assert record.source == 'EXCEL_IMPORT'
        assert record.check_in_at.strftime('%H:%M') == '09:05'
        assert record.check_out_at.strftime('%H:%M') == '18:12'

    def test_attendance_sheet_import_fails_without_partial_post(self, attendance_setup):
        client = attendance_setup['client']
        workbook_bytes = build_xlsx(
            ['employee_code', 'date', 'check_in', 'check_out'],
            [
                ['EMP100', '2026-04-02', '09:05', '18:12'],
                ['UNKNOWN', '2026-04-02', '09:00', '18:00'],
            ],
        )

        response = client.post(
            '/api/org/attendance/imports/attendance-sheet/',
            {'file': SimpleUploadedFile('attendance.xlsx', workbook_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},
        )

        assert response.status_code == 201
        assert response.data['status'] == AttendanceImportStatus.FAILED
        assert response.data['error_rows'] == 1
        assert AttendanceRecord.objects.count() == 0

    def test_punch_sheet_import_generates_normalized_download(self, attendance_setup):
        client = attendance_setup['client']
        workbook_bytes = build_xlsx(
            ['employee_code', 'date', 'punch_time'],
            [
                ['EMP100', '2026-04-03', '09:01'],
                ['EMP100', '2026-04-03', '13:02'],
                ['EMP100', '2026-04-03', '18:04'],
            ],
        )

        upload_response = client.post(
            '/api/org/attendance/imports/punch-sheet/',
            {'file': SimpleUploadedFile('punches.xlsx', workbook_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},
        )

        assert upload_response.status_code == 201
        assert upload_response.data['status'] == AttendanceImportStatus.READY_FOR_REVIEW
        assert upload_response.data['valid_rows'] == 1
        job_id = upload_response.data['id']

        download_response = client.get(f'/api/org/attendance/imports/{job_id}/normalized-file/')

        assert download_response.status_code == 200
        workbook = load_workbook(BytesIO(download_response.content))
        rows = list(workbook.active.iter_rows(values_only=True))
        assert rows[0] == ('employee_code', 'date', 'check_in', 'check_out')
        assert rows[1] == ('EMP100', '2026-04-03', '09:01', '18:04')

    def test_punch_sheet_import_marks_single_punch_days_for_review(self, attendance_setup):
        client = attendance_setup['client']
        workbook_bytes = build_xlsx(
            ['employee_code', 'date', 'punch_time'],
            [['EMP100', '2026-04-04', '09:30']],
        )

        upload_response = client.post(
            '/api/org/attendance/imports/punch-sheet/',
            {'file': SimpleUploadedFile('punches.xlsx', workbook_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},
        )

        assert upload_response.status_code == 201
        assert upload_response.data['status'] == AttendanceImportStatus.READY_FOR_REVIEW

        workbook = load_workbook(BytesIO(client.get(f"/api/org/attendance/imports/{upload_response.data['id']}/normalized-file/").content))
        review_sheet = workbook['Review Notes']
        assert review_sheet['A2'].value == 'EMP100'
        assert review_sheet['D2'].value == 'Only one punch was found for this employee on this date. Add a checkout time before re-uploading.'

