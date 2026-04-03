
import pytest
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIClient

from apps.accounts.models import AccountType, User, UserRole
from apps.approvals.models import ApprovalRun, ApprovalWorkflow
from apps.attendance.models import (
    AttendanceImportJob,
    AttendanceImportStatus,
    AttendancePolicy,
    AttendanceRegularizationRequest,
    AttendanceRegularizationStatus,
    AttendanceSourceConfig,
)
from apps.documents.models import Document, EmployeeDocumentRequest, OnboardingDocumentType
from apps.employees.models import (
    Employee,
    EmployeeBankAccount,
    EmployeeEmergencyContact,
    EmployeeFamilyMember,
    EmployeeGovernmentId,
    EmployeeProfile,
)
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationAddress,
    OrganisationAddressType,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationNote,
    OrganisationStatus,
)
from apps.payroll.models import (
    CompensationAssignment,
    CompensationAssignmentStatus,
    CompensationTemplate,
    PayrollRun,
    PayrollRunItem,
    PayrollTaxSlabSet,
)


def organisation_create_payload(name='New Org'):
    return {
        'name': name,
        'pan_number': 'ABCDE1234F',
        'country_code': 'IN',
        'currency': 'INR',
        'entity_type': 'PRIVATE_LIMITED',
        'primary_admin': {
            'first_name': 'Aditi',
            'last_name': 'Rao',
            'email': 'admin@test.com',
            'phone': '+919876543210',
        },
        'addresses': [
            {
                'address_type': 'REGISTERED',
                'line1': '123 Main St',
                'city': 'Bengaluru',
                'state': 'Karnataka',
                'country': 'India',
                'pincode': '560001',
                'gstin': '29ABCDE1234F1Z5',
            },
            {
                'address_type': 'BILLING',
                'line1': '18 Nariman Point',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'country': 'India',
                'pincode': '400021',
                'gstin': '27ABCDE1234F1Z7',
            },
        ],
    }


@pytest.fixture
def ct_client(db):
    user = User.objects.create_superuser(
        email='ct@test.com', password='pass123!',
        first_name='Control', last_name='Tower', role=UserRole.CONTROL_TOWER,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def org(db):
    ct_user = User.objects.create_superuser(
        email='ct2@test.com', password='pass123!', role=UserRole.CONTROL_TOWER,
    )
    return Organisation.objects.create(name='Test Corp', licence_count=10, created_by=ct_user)


@pytest.mark.django_db
class TestOrganisationListCreate:
    def test_list_returns_paginated_orgs(self, ct_client, org):
        client, _ = ct_client
        response = client.get('/api/ct/organisations/')
        assert response.status_code == 200
        assert response.data['count'] >= 1

    def test_create_org(self, ct_client):
        client, _ = ct_client
        response = client.post('/api/ct/organisations/', organisation_create_payload(), format='json')
        assert response.status_code == 201
        assert response.data['name'] == 'New Org'
        assert response.data['status'] == OrganisationStatus.PENDING
        assert response.data['pan_number'] == 'ABCDE1234F'
        assert response.data['phone'] == ''
        assert response.data['country_code'] == 'IN'
        assert response.data['currency'] == 'INR'
        assert response.data['entity_type'] == 'PRIVATE_LIMITED'
        assert response.data['bootstrap_admin']['email'] == 'admin@test.com'

    def test_create_requires_name(self, ct_client):
        client, _ = ct_client
        response = client.post('/api/ct/organisations/', {}, format='json')
        assert response.status_code == 400

    def test_create_rejects_phone_with_wrong_country_dial_code(self, ct_client):
        client, _ = ct_client
        payload = organisation_create_payload()
        payload['primary_admin']['phone'] = '+447700900123'
        payload['country_code'] = 'IN'
        response = client.post('/api/ct/organisations/', payload, format='json')
        assert response.status_code == 400
        assert 'primary_admin' in response.data

    def test_create_returns_400_for_duplicate_gstin(self, ct_client):
        client, _ = ct_client
        first_response = client.post('/api/ct/organisations/', organisation_create_payload(name='Existing Org'), format='json')
        assert first_response.status_code == 201
        payload = organisation_create_payload(name='Conflicting Org')
        payload['addresses'][0]['gstin'] = '29ABCDE1234F1Z5'
        response = client.post('/api/ct/organisations/', payload, format='json')
        assert response.status_code == 400
        assert 'error' in response.data

    def test_create_reuses_existing_person_for_bootstrap_admin_email(self, ct_client):
        client, _ = ct_client
        user = User.objects.create_user(
            email='admin@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.ORG_ADMIN,
            is_active=True,
        )

        response = client.post('/api/ct/organisations/', organisation_create_payload(name='Shared Person Org'), format='json')

        assert response.status_code == 201
        organisation = Organisation.objects.get(id=response.data['id'])
        assert organisation.bootstrap_admin.person_id == user.person_id

    def test_create_rejects_email_and_phone_that_resolve_to_different_people(self, ct_client):
        client, _ = ct_client
        User.objects.create_user(
            email='someoneelse@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        User.objects.create_user(
            email='new-admin@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.ORG_ADMIN,
            is_active=True,
        )
        payload = organisation_create_payload(name='Phone Conflict Org')
        payload['primary_admin']['email'] = 'new-admin@test.com'
        payload['primary_admin']['phone'] = '+919900001111'
        conflicting_user = User.objects.get(email='someoneelse@test.com', account_type=AccountType.WORKFORCE)
        conflicting_user.person.phone_numbers.create(
            e164_number='+919900001111',
            display_number='+91 99000 01111',
            kind='WORK',
            is_primary=True,
        )

        response = client.post('/api/ct/organisations/', payload, format='json')

        assert response.status_code == 400
        assert 'error' in response.data

    def test_unauthenticated_returns_401(self):
        client = APIClient()
        response = client.get('/api/ct/organisations/')
        assert response.status_code == 403

    def test_non_ct_user_returns_403(self, db):
        ct = User.objects.create_superuser(email='seed@test.com', password='pass', role=UserRole.CONTROL_TOWER)
        org = Organisation.objects.create(
            name='Org',
            licence_count=5,
            created_by=ct,
            status=OrganisationStatus.ACTIVE,
            billing_status=OrganisationBillingStatus.PAID,
            access_state=OrganisationAccessState.ACTIVE,
        )
        user = User.objects.create_user(email='org@test.com', password='pass', role=UserRole.ORG_ADMIN, is_active=True)
        OrganisationMembership.objects.create(
            user=user,
            organisation=org,
            is_org_admin=True,
            status=OrganisationMembershipStatus.ACTIVE,
        )
        client = APIClient()
        client.post('/api/auth/login/', {'email': 'org@test.com', 'password': 'pass'}, format='json')
        response = client.get('/api/ct/organisations/')
        assert response.status_code == 403


@pytest.mark.django_db
class TestOrganisationActivate:
    def test_pending_to_paid(self, ct_client, org):
        client, _ = ct_client
        response = client.post(f'/api/ct/organisations/{org.id}/activate/')
        assert response.status_code == 200
        assert response.data['status'] == OrganisationStatus.PAID

    def test_invalid_transition_returns_400(self, ct_client, org):
        client, _ = ct_client
        # PENDING cannot go to SUSPENDED
        response = client.post(f'/api/ct/organisations/{org.id}/suspend/')
        assert response.status_code == 400


@pytest.mark.django_db
class TestOrganisationProfileUpdate:
    def test_control_tower_update_rejects_phone_with_wrong_country_dial_code(self, ct_client):
        client, user = ct_client
        organisation = Organisation.objects.create(
            name='Acme Corp',
            created_by=user,
            country_code='IN',
            currency='INR',
        )
        response = client.patch(
            f'/api/ct/organisations/{organisation.id}/',
            {'phone': '+447700900123'},
            format='json',
        )
        assert response.status_code == 400
        assert 'phone' in response.data


@pytest.mark.django_db
class TestLicenceBatchViews:
    def test_org_detail_includes_batch_defaults_and_batches(self, ct_client, org):
        client, _ = ct_client

        response = client.get(f'/api/ct/organisations/{org.id}/')

        assert response.status_code == 200
        assert 'licence_batches' in response.data
        assert 'batch_defaults' in response.data
        assert response.data['licence_batches'] == []

    def test_create_update_and_mark_paid_batch(self, ct_client, org):
        client, _ = ct_client

        create_response = client.post(
            f'/api/ct/organisations/{org.id}/licence-batches/',
            {
                'quantity': 5,
                'price_per_licence_per_month': '99.00',
                'start_date': '2026-04-01',
                'end_date': '2026-12-31',
                'note': 'Initial commercial batch',
            },
            format='json',
        )

        assert create_response.status_code == 201
        assert create_response.data['payment_status'] == 'DRAFT'
        assert create_response.data['lifecycle_state'] == 'DRAFT'

        batch_id = create_response.data['id']
        update_response = client.patch(
            f'/api/ct/organisations/{org.id}/licence-batches/{batch_id}/',
            {
                'quantity': 6,
                'price_per_licence_per_month': '109.00',
            },
            format='json',
        )
        assert update_response.status_code == 200
        assert update_response.data['quantity'] == 6
        assert update_response.data['price_per_licence_per_month'] == '109.00'

        pay_response = client.post(
            f'/api/ct/organisations/{org.id}/licence-batches/{batch_id}/mark-paid/',
            {'paid_at': '2026-04-01'},
            format='json',
        )

        assert pay_response.status_code == 200
        assert pay_response.data['payment_status'] == 'PAID'
        assert pay_response.data['lifecycle_state'] in ['ACTIVE', 'PAID_PENDING_START']


@pytest.mark.django_db
class TestCtOrganisationDetailTabsSupport:
    def test_org_detail_includes_tab_summary_counts(self, ct_client, org):
        client, ct_user = ct_client
        response = client.get(f'/api/ct/organisations/{org.id}/')

        assert response.status_code == 200
        assert 'admin_count' in response.data
        assert 'employee_count' in response.data
        assert 'holiday_calendar_count' in response.data
        assert 'note_count' in response.data
        assert 'configuration_summary' in response.data

    def test_org_detail_includes_operations_guard_for_blocked_orgs(self, ct_client, org):
        client, _ = ct_client

        response = client.get(f'/api/ct/organisations/{org.id}/')

        assert response.status_code == 200
        assert response.data['operations_guard'] == {
            'licence_expired': True,
            'admin_mutations_blocked': True,
            'approval_actions_blocked': True,
            'seat_assignment_blocked': True,
            'reason': 'Organisation licences have expired. Renew licences in Control Tower to continue.',
            'summary': response.data['operations_guard']['summary'],
        }
        assert response.data['operations_guard']['summary']['active_paid_quantity'] == 0

    def test_ct_can_create_and_list_notes(self, ct_client, org):
        client, ct_user = ct_client

        create_response = client.post(
            f'/api/ct/organisations/{org.id}/notes/',
            {'body': 'Payment follow-up scheduled with finance.'},
            format='json',
        )

        assert create_response.status_code == 201
        assert create_response.data['body'] == 'Payment follow-up scheduled with finance.'
        assert create_response.data['created_by']['email'] == ct_user.email
        assert OrganisationNote.objects.filter(organisation=org).count() == 1

        list_response = client.get(f'/api/ct/organisations/{org.id}/notes/')

        assert list_response.status_code == 200
        assert len(list_response.data) == 1
        assert list_response.data[0]['created_by']['email'] == ct_user.email
        assert list_response.data[0]['created_at']

    def test_ct_can_list_employees_for_org(self, ct_client, org):
        client, _ = ct_client
        workforce_user = User.objects.create_user(
            email='employee@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            is_active=True,
            first_name='Riya',
            last_name='Sen',
        )

        employee = Employee.objects.create(
            organisation=org,
            user=workforce_user,
            designation='Analyst',
            employment_type='FULL_TIME',
            status='ACTIVE',
        )

        response = client.get(f'/api/ct/organisations/{org.id}/employees/')

        assert response.status_code == 200
        assert response.data['count'] == 1
        assert response.data['results'][0]['full_name'] == 'Riya Sen'
        assert response.data['results'][0]['designation'] == 'Analyst'
        assert 'email' not in response.data['results'][0]
        assert 'employment_type' not in response.data['results'][0]
        assert 'date_of_joining' not in response.data['results'][0]

        detail_response = client.get(f'/api/ct/organisations/{org.id}/employees/{employee.id}/')
        assert detail_response.status_code == 200
        assert detail_response.data['full_name'] == 'Riya Sen'
        assert 'email' not in detail_response.data
        assert 'profile' not in detail_response.data
        assert 'government_ids' not in detail_response.data
        assert 'bank_accounts' not in detail_response.data
        assert 'family_members' not in detail_response.data
        assert 'emergency_contacts' not in detail_response.data

    def test_ct_employee_detail_hides_sensitive_employee_data(self, ct_client, org):
        client, _ = ct_client
        manager_user = User.objects.create_user(
            email='manager@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            is_active=True,
            first_name='Meera',
            last_name='Kapoor',
        )
        manager = Employee.objects.create(
            organisation=org,
            user=manager_user,
            employee_code='EMP001',
            designation='Manager',
            employment_type='FULL_TIME',
            status='ACTIVE',
        )
        workforce_user = User.objects.create_user(
            email='private.employee@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            is_active=True,
            first_name='Asha',
            last_name='Iyer',
        )
        employee = Employee.objects.create(
            organisation=org,
            user=workforce_user,
            employee_code='EMP002',
            designation='Engineer',
            employment_type='FULL_TIME',
            status='ACTIVE',
            onboarding_status='BASIC_DETAILS_PENDING',
            reporting_to=manager,
        )
        EmployeeProfile.objects.create(
            employee=employee,
            phone_personal='+919999999999',
            nationality='Indian',
            address_line1='Secret address',
            city='Bengaluru',
            state='Karnataka',
            country='India',
            pincode='560001',
        )
        EmployeeGovernmentId.objects.create(
            employee=employee,
            id_type='PAN',
            masked_identifier='ABCDE1234F',
            name_on_id='Asha Iyer',
        )
        EmployeeBankAccount.objects.create(
            employee=employee,
            account_holder_name='Asha Iyer',
            bank_name='Test Bank',
            masked_account_number='XXXX1234',
            masked_ifsc='XXXX0001234',
            is_primary=True,
        )
        EmployeeFamilyMember.objects.create(
            employee=employee,
            full_name='Raman Iyer',
            relation='FATHER',
            contact_number='+919888888888',
        )
        EmployeeEmergencyContact.objects.create(
            employee=employee,
            full_name='Neha Iyer',
            relation='Spouse',
            phone_number='+919777777777',
            address='Another secret address',
            is_primary=True,
        )

        response = client.get(f'/api/ct/organisations/{org.id}/employees/{employee.id}/')

        assert response.status_code == 200
        assert response.data == {
            'id': str(employee.id),
            'employee_code': 'EMP002',
            'full_name': 'Asha Iyer',
            'designation': 'Engineer',
            'employment_type': 'FULL_TIME',
            'date_of_joining': None,
            'date_of_exit': None,
            'status': 'ACTIVE',
            'onboarding_status': 'BASIC_DETAILS_PENDING',
            'department_name': None,
            'office_location_name': None,
            'reporting_to_name': 'Meera Kapoor',
        }

    def test_ct_cannot_edit_employee_records(self, ct_client, org):
        client, _ = ct_client
        workforce_user = User.objects.create_user(
            email='locked.employee@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            is_active=True,
            first_name='Locked',
            last_name='User',
        )
        employee = Employee.objects.create(
            organisation=org,
            user=workforce_user,
            designation='Analyst',
            employment_type='FULL_TIME',
            status='ACTIVE',
        )

        response = client.patch(
            f'/api/ct/organisations/{org.id}/employees/{employee.id}/',
            {'designation': 'Senior Analyst'},
            format='json',
        )

        employee.refresh_from_db()
        assert response.status_code == 405
        assert employee.designation == 'Analyst'

    def test_ct_can_manage_holiday_calendars(self, ct_client, org):
        client, _ = ct_client

        create_response = client.post(
            f'/api/ct/organisations/{org.id}/holiday-calendars/',
            {
                'name': 'FY 2026 Calendar',
                'year': 2026,
                'description': '',
                'is_default': True,
                'holidays': [
                    {
                        'name': 'Founders Day',
                        'holiday_date': '2026-07-15',
                        'classification': 'COMPANY',
                        'session': 'FULL_DAY',
                        'description': '',
                    }
                ],
                'location_ids': [],
            },
            format='json',
        )

        assert create_response.status_code == 201
        calendar_id = create_response.data['id']

        publish_response = client.post(f'/api/ct/organisations/{org.id}/holiday-calendars/{calendar_id}/publish/')
        assert publish_response.status_code == 200
        assert publish_response.data['status'] == 'PUBLISHED'

    def test_ct_can_fetch_configuration_snapshot(self, ct_client, org):
        client, _ = ct_client

        response = client.get(f'/api/ct/organisations/{org.id}/configuration/')

        assert response.status_code == 200
        assert set(response.data.keys()) == {
            'locations',
            'departments',
            'leave_cycles',
            'leave_plans',
            'on_duty_policies',
            'approval_workflows',
            'notices',
        }

    def test_ct_payroll_support_summary_is_sanitized(self, ct_client, org):
        client, _ = ct_client
        workforce_user = User.objects.create_user(
            email='payroll.employee@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            is_active=True,
            first_name='Ira',
            last_name='Nair',
        )
        employee = Employee.objects.create(
            organisation=org,
            user=workforce_user,
            employee_code='EMP900',
            designation='Operator',
            employment_type='FULL_TIME',
            status='ACTIVE',
        )
        pay_run = PayrollRun.objects.create(
            organisation=org,
            name='April Payroll',
            period_year=2026,
            period_month=4,
            status='CALCULATED',
        )
        PayrollRunItem.objects.create(
            pay_run=pay_run,
            employee=employee,
            status='EXCEPTION',
            message='No approved compensation assignment is effective for this period.',
        )

        response = client.get(f'/api/ct/organisations/{org.id}/payroll/')

        assert response.status_code == 200
        assert response.data['payroll_runs'][0] == {
            'id': str(pay_run.id),
            'name': 'April Payroll',
            'period_year': 2026,
            'period_month': 4,
            'run_type': 'REGULAR',
            'status': 'CALCULATED',
            'created_at': response.data['payroll_runs'][0]['created_at'],
            'calculated_at': None,
            'submitted_at': None,
            'finalized_at': None,
            'ready_count': 0,
            'exception_count': 1,
            'exception_messages': ['No approved compensation assignment is effective for this period.'],
            'attendance_snapshot_summary': {
                'attendance_source': '',
                'period_start': None,
                'period_end': None,
                'use_attendance_inputs': False,
                'employee_count': 0,
                'ready_item_count': 0,
                'exception_item_count': 0,
                'total_attendance_paid_days': '0.00',
                'total_lop_days': '0.00',
                'total_overtime_minutes': 0,
            },
        }
        assert {item['code'] for item in response.data['diagnostics']} == {
            'MISSING_TAX_SLAB_SET',
            'NO_COMPENSATION_TEMPLATES',
            'NO_APPROVED_ASSIGNMENTS',
            'RUN_EXCEPTIONS_PRESENT',
        }
        assert 'items' not in response.data['payroll_runs'][0]
        assert 'gross_pay' not in response.data['payroll_runs'][0]
        assert 'net_pay' not in response.data['payroll_runs'][0]

    def test_ct_payroll_support_summary_surfaces_pending_assignment_gaps(self, ct_client, org):
        client, _ = ct_client
        workforce_user = User.objects.create_user(
            email='pending.payroll.employee@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            is_active=True,
            first_name='Riya',
            last_name='Das',
        )
        employee = Employee.objects.create(
            organisation=org,
            user=workforce_user,
            employee_code='EMP902',
            designation='Analyst',
            employment_type='FULL_TIME',
            status='ACTIVE',
        )
        PayrollTaxSlabSet.objects.create(
            organisation=org,
            name='FY 2026-27',
            fiscal_year='2026-27',
            country_code='IN',
            is_active=True,
        )
        template = CompensationTemplate.objects.create(
            organisation=org,
            name='Analyst template',
            status='APPROVED',
        )
        CompensationAssignment.objects.create(
            employee=employee,
            template=template,
            effective_from='2026-04-01',
            status=CompensationAssignmentStatus.PENDING_APPROVAL,
        )

        response = client.get(f'/api/ct/organisations/{org.id}/payroll/')

        assert response.status_code == 200
        assert response.data['tax_slab_set_count'] == 1
        assert response.data['compensation_template_count'] == 1
        assert response.data['pending_assignment_count'] == 1
        assert {item['code'] for item in response.data['diagnostics']} == {
            'NO_APPROVED_ASSIGNMENTS',
            'PENDING_ASSIGNMENTS',
        }

    def test_ct_approval_support_summary_exposes_run_state_without_inline_actions(self, ct_client, org):
        client, _ = ct_client
        workflow = ApprovalWorkflow.objects.create(
            organisation=org,
            name='Leave workflow',
            is_active=True,
        )
        ApprovalRun.objects.create(
            organisation=org,
            workflow=workflow,
            request_kind='LEAVE',
            status='PENDING',
            current_stage_sequence=1,
            subject_label='Sick leave request',
            content_type_id=ContentType.objects.get_for_model(Organisation).id,
            object_id=org.id,
        )

        response = client.get(f'/api/ct/organisations/{org.id}/approvals/')

        assert response.status_code == 200
        assert response.data['workflows_count'] == 1
        assert response.data['pending_runs_count'] == 1
        assert response.data['recent_runs'][0]['subject_label'] == 'Sick leave request'
        assert response.data['recent_runs'][0]['workflow_name'] == 'Leave workflow'
        assert response.data['recent_runs'][0]['pending_actions_count'] == 0
        assert 'actions' not in response.data['recent_runs'][0]

    def test_ct_attendance_support_summary_is_sanitized(self, ct_client, org):
        client, _ = ct_client
        workforce_user = User.objects.create_user(
            email='attendance.employee@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            is_active=True,
            first_name='Anaya',
            last_name='Sen',
        )
        employee = Employee.objects.create(
            organisation=org,
            user=workforce_user,
            employee_code='EMP901',
            designation='Operator',
            employment_type='FULL_TIME',
            status='ACTIVE',
        )
        AttendancePolicy.objects.create(
            organisation=org,
            name='Default Attendance Policy',
            is_default=True,
            is_active=True,
        )
        AttendanceSourceConfig.objects.create(
            organisation=org,
            name='Gateway',
            kind='API',
            configuration={'api_key_hash': 'hash', 'api_key_encrypted': 'encrypted'},
            is_active=True,
        )
        AttendanceRegularizationRequest.objects.create(
            organisation=org,
            employee=employee,
            attendance_date='2026-04-07',
            reason='Missed punch',
            status=AttendanceRegularizationStatus.PENDING,
        )
        AttendanceImportJob.objects.create(
            organisation=org,
            mode='ATTENDANCE_SHEET',
            status=AttendanceImportStatus.POSTED,
            original_filename='attendance.xlsx',
            valid_rows=1,
            error_rows=0,
            posted_rows=1,
        )

        response = client.get(f'/api/ct/organisations/{org.id}/attendance/')

        assert response.status_code == 200
        assert response.data['policy_count'] == 1
        assert response.data['source_count'] == 1
        assert response.data['active_source_count'] == 1
        assert response.data['pending_regularizations'] == 1
        assert {item['code'] for item in response.data['diagnostics']} == {'PENDING_REGULARIZATIONS'}
        assert response.data['recent_imports'][0]['original_filename'] == 'attendance.xlsx'
        assert 'days' not in response.data

    def test_ct_attendance_support_summary_surfaces_setup_gaps(self, ct_client, org):
        client, _ = ct_client

        response = client.get(f'/api/ct/organisations/{org.id}/attendance/')

        assert response.status_code == 200
        assert 'NO_ACTIVE_ATTENDANCE_SOURCE' in {item['code'] for item in response.data['diagnostics']}

    def test_ct_onboarding_support_summary_is_sanitized(self, ct_client, org):
        client, _ = ct_client
        document_type = OnboardingDocumentType.objects.create(
            code='BANK_PASSBOOK_AUDIT',
            name='Bank Passbook',
            category='BANKING_PAYROLL',
        )
        employee_user = User.objects.create_user(
            email='doc.employee@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            is_active=True,
            first_name='Nisha',
            last_name='Patel',
        )
        employee = Employee.objects.create(
            organisation=org,
            user=employee_user,
            employee_code='EMP777',
            designation='Coordinator',
            employment_type='FULL_TIME',
            status='ACTIVE',
            onboarding_status='DOCUMENTS_PENDING',
        )
        request = EmployeeDocumentRequest.objects.create(
            employee=employee,
            document_type_ref=document_type,
            is_required=True,
            status='REJECTED',
            rejection_note='Unreadable copy',
        )
        Document.objects.create(
            employee=employee,
            document_request=request,
            document_type='BANK_PASSBOOK_AUDIT',
            file_key='organisations/test/employees/EMP777/bank-passbook/test.pdf',
            file_name='passbook.pdf',
            file_size=128,
            mime_type='application/pdf',
            status='REJECTED',
            metadata={'rejection_note': 'Unreadable copy'},
        )

        response = client.get(f'/api/ct/organisations/{org.id}/onboarding-support/')

        assert response.status_code == 200
        assert response.data['onboarding_status_counts'] == {
            'NOT_STARTED': 0,
            'BASIC_DETAILS_PENDING': 0,
            'DOCUMENTS_PENDING': 1,
            'COMPLETE': 0,
        }
        assert response.data['document_request_status_counts'] == {
            'REQUESTED': 0,
            'SUBMITTED': 0,
            'VERIFIED': 0,
            'REJECTED': 1,
            'WAIVED': 0,
        }
        assert response.data['blocked_employees'][0] == {
            'id': str(employee.id),
            'employee_code': 'EMP777',
            'full_name': 'Nisha Patel',
            'designation': 'Coordinator',
            'status': 'ACTIVE',
            'onboarding_status': 'DOCUMENTS_PENDING',
            'pending_document_requests': 1,
            'latest_document_activity_at': response.data['blocked_employees'][0]['latest_document_activity_at'],
        }
        assert response.data['top_blocker_types'][0]['document_type_name'] == 'Bank Passbook'
        assert response.data['top_blocker_types'][0]['blocked_employee_count'] == 1
        assert 'rejection_note' not in response.data['blocked_employees'][0]
        assert 'metadata' not in response.data['blocked_employees'][0]


@pytest.mark.django_db
class TestCtOrganisationEditingParity:
    def test_ct_admin_list_includes_invited_and_inactive_memberships(self, ct_client, org):
        client, _ = ct_client
        invited_user = User.objects.create_user(
            email='pending-admin@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.ORG_ADMIN,
            is_active=False,
        )
        inactive_user = User.objects.create_user(
            email='inactive-admin@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.ORG_ADMIN,
            is_active=True,
        )
        OrganisationMembership.objects.create(
            user=invited_user,
            organisation=org,
            is_org_admin=True,
            status=OrganisationMembershipStatus.INVITED,
        )
        OrganisationMembership.objects.create(
            user=inactive_user,
            organisation=org,
            is_org_admin=True,
            status=OrganisationMembershipStatus.INACTIVE,
        )

        response = client.get(f'/api/ct/organisations/{org.id}/admins/')

        assert response.status_code == 200
        assert {item['membership_status'] for item in response.data} >= {'INVITED', 'INACTIVE'}

    def test_ct_can_deactivate_and_reactivate_additional_org_admin(self, ct_client, org):
        client, ct_user = ct_client
        primary = User.objects.create_user(
            email='primary@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.ORG_ADMIN,
            is_active=True,
        )
        secondary = User.objects.create_user(
            email='secondary@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.ORG_ADMIN,
            is_active=True,
        )
        org.primary_admin_user = primary
        org.save(update_fields=['primary_admin_user', 'modified_at'])
        OrganisationMembership.objects.create(
            user=primary,
            organisation=org,
            is_org_admin=True,
            status=OrganisationMembershipStatus.ACTIVE,
            invited_by=ct_user,
        )
        OrganisationMembership.objects.create(
            user=secondary,
            organisation=org,
            is_org_admin=True,
            status=OrganisationMembershipStatus.ACTIVE,
            invited_by=ct_user,
        )

        deactivate_response = client.post(f'/api/ct/organisations/{org.id}/admins/{secondary.id}/deactivate/')
        reactivate_response = client.post(f'/api/ct/organisations/{org.id}/admins/{secondary.id}/reactivate/')

        assert deactivate_response.status_code == 200
        assert deactivate_response.data['membership_status'] == 'INACTIVE'
        assert reactivate_response.status_code == 200
        assert reactivate_response.data['membership_status'] == 'ACTIVE'

    def test_ct_can_revoke_pending_admin_invite(self, ct_client, org):
        client, ct_user = ct_client
        pending_user = User.objects.create_user(
            email='revoke-admin@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.ORG_ADMIN,
            is_active=False,
        )
        OrganisationMembership.objects.create(
            user=pending_user,
            organisation=org,
            is_org_admin=True,
            status=OrganisationMembershipStatus.INVITED,
            invited_by=ct_user,
        )

        response = client.post(f'/api/ct/organisations/{org.id}/admins/{pending_user.id}/revoke-pending/')

        assert response.status_code == 200
        assert response.data['membership_status'] == 'REVOKED'

    def test_ct_can_manage_locations_and_departments(self, ct_client, org):
        client, _ = ct_client
        registered_address = OrganisationAddress.objects.create(
            organisation=org,
            address_type=OrganisationAddressType.REGISTERED,
            label='Registered Office',
            line1='1 Residency Road',
            city='Bengaluru',
            state='Karnataka',
            state_code='KA',
            country='India',
            country_code='IN',
            pincode='560001',
            is_active=True,
        )
        OrganisationAddress.objects.create(
            organisation=org,
            address_type=OrganisationAddressType.BILLING,
            label='Billing Address',
            line1='2 MG Road',
            city='Bengaluru',
            state='Karnataka',
            state_code='KA',
            country='India',
            country_code='IN',
            pincode='560002',
            gstin='29ABCDE1234F1Z5',
            is_active=True,
        )

        location_response = client.post(
            f'/api/ct/organisations/{org.id}/locations/',
            {'name': 'HQ', 'organisation_address_id': str(registered_address.id), 'is_remote': False},
            format='json',
        )
        department_response = client.post(
            f'/api/ct/organisations/{org.id}/departments/',
            {'name': 'Engineering', 'description': 'Product engineering'},
            format='json',
        )

        assert location_response.status_code == 201
        assert location_response.data['name'] == 'HQ'
        assert department_response.status_code == 201
        assert department_response.data['name'] == 'Engineering'

    def test_ct_can_manage_leave_and_notice_configuration(self, ct_client, org):
        client, _ = ct_client
        cycle_response = client.post(
            f'/api/ct/organisations/{org.id}/leave-cycles/',
            {
                'name': 'Calendar Year',
                'cycle_type': 'CALENDAR_YEAR',
                'start_month': 1,
                'start_day': 1,
                'is_default': True,
                'is_active': True,
            },
            format='json',
        )
        assert cycle_response.status_code == 201

        plan_response = client.post(
            f'/api/ct/organisations/{org.id}/leave-plans/',
            {
                'leave_cycle_id': cycle_response.data['id'],
                'name': 'General Plan',
                'description': '',
                'is_default': True,
                'is_active': True,
                'priority': 100,
                'leave_types': [
                    {
                        'code': 'CL',
                        'name': 'Casual Leave',
                        'annual_entitlement': '12.00',
                        'credit_frequency': 'MONTHLY',
                    }
                ],
                'rules': [],
            },
            format='json',
        )
        policy_response = client.post(
            f'/api/ct/organisations/{org.id}/on-duty-policies/',
            {
                'name': 'Default Policy',
                'description': '',
                'is_default': True,
                'is_active': True,
                'allow_half_day': True,
                'allow_time_range': True,
                'requires_attachment': False,
            },
            format='json',
        )
        workflow_response = client.post(
            f'/api/ct/organisations/{org.id}/approval-workflows/',
            {
                'name': 'Default Workflow',
                'description': '',
                'is_default': True,
                'default_request_kind': 'LEAVE',
                'is_active': True,
                'rules': [{'name': 'Default leave rule', 'request_kind': 'LEAVE', 'priority': 100, 'is_active': True}],
                'stages': [
                    {
                        'name': 'Primary admin approval',
                        'sequence': 1,
                        'mode': 'ALL',
                        'fallback_type': 'PRIMARY_ORG_ADMIN',
                        'approvers': [{'approver_type': 'PRIMARY_ORG_ADMIN'}],
                    }
                ],
            },
            format='json',
        )
        notice_response = client.post(
            f'/api/ct/organisations/{org.id}/notices/',
            {
                'title': 'Office advisory',
                'body': 'Quarter-end blackout window',
                'audience_type': 'ALL_EMPLOYEES',
                'status': 'DRAFT',
            },
            format='json',
        )

        assert plan_response.status_code == 201
        assert policy_response.status_code == 201
        assert workflow_response.status_code == 201
        assert notice_response.status_code == 201

        publish_response = client.post(
            f"/api/ct/organisations/{org.id}/notices/{notice_response.data['id']}/publish/"
        )
        assert publish_response.status_code == 200
        assert publish_response.data['status'] == 'PUBLISHED'
