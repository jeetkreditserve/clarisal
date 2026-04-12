from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
from apps.approvals.models import (
    ApprovalAction,
    ApprovalActionStatus,
    ApprovalApproverType,
    ApprovalDelegation,
    ApprovalFallbackType,
    ApprovalRequestKind,
    ApprovalRun,
    ApprovalRunStatus,
    ApprovalStage,
    ApprovalStageApprover,
    ApprovalWorkflow,
)
from apps.employees.models import Employee, EmployeeStatus
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationStatus,
)
from apps.organisations.services import create_licence_batch, mark_licence_batch_paid


def _create_pending_action(*, organisation, requester, approver_user, subject, request_kind, subject_label):
    workflow = ApprovalWorkflow.objects.create(
        organisation=organisation,
        name=f'{subject_label} Workflow',
        is_active=True,
    )
    stage = ApprovalStage.objects.create(
        workflow=workflow,
        name='Primary review',
        sequence=1,
    )
    return ApprovalAction.objects.create(
        approval_run=ApprovalRun.objects.create(
            organisation=organisation,
            workflow=workflow,
            request_kind=request_kind,
            requested_by=requester,
            requested_by_user=requester.user,
            status=ApprovalRunStatus.PENDING,
            current_stage_sequence=stage.sequence,
            subject_label=subject_label,
            content_type=ContentType.objects.get_for_model(subject.__class__),
            object_id=subject.id,
        ),
        stage=stage,
        approver_user=approver_user,
    )


@pytest.fixture
def org_admin_client(db):
    today = timezone.localdate()
    organisation = Organisation.objects.create(
        name='Acme Corp',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    user = User.objects.create_user(
        email='admin@test.com',
        password='pass123!',
        role=UserRole.ORG_ADMIN,
        is_active=True,
    )
    OrganisationMembership.objects.create(
        user=user,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
    )
    paid_batch = create_licence_batch(
        organisation=organisation,
        quantity=5,
        price_per_licence_per_month=Decimal('100.00'),
        start_date=today - timedelta(days=7),
        end_date=today + timedelta(days=30),
        created_by=user,
    )
    mark_licence_batch_paid(paid_batch, paid_by=user, paid_at=today - timedelta(days=1))
    client = APIClient()
    client.force_authenticate(user=user)
    session = client.session
    session['active_workspace_kind'] = 'ADMIN'
    session['active_admin_org_id'] = str(organisation.id)
    session.save()
    return client, organisation


@pytest.fixture
def employee_client(org_admin_client):
    _, organisation = org_admin_client
    user = User.objects.create_user(
        email='employee-view@test.com',
        password='pass123!',
        role=UserRole.EMPLOYEE,
        is_active=True,
    )
    employee = Employee.objects.create(
        organisation=organisation,
        user=user,
        employee_code='EMP-VIEW',
        status=EmployeeStatus.ACTIVE,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    session = client.session
    session['active_workspace_kind'] = 'EMPLOYEE'
    session['active_employee_id'] = str(employee.id)
    session.save()
    return client, organisation, employee


@pytest.mark.django_db
class TestApprovalWorkflowApi:
    def test_create_accepts_attendance_regularization_defaults(self, org_admin_client):
        client, organisation = org_admin_client

        response = client.post(
            '/api/v1/org/approvals/workflows/',
            {
                'name': 'Attendance Regularization Workflow',
                'description': '',
                'is_default': True,
                'default_request_kind': ApprovalRequestKind.ATTENDANCE_REGULARIZATION,
                'is_active': True,
                'rules': [
                    {
                        'name': 'Default regularization rule',
                        'request_kind': ApprovalRequestKind.ATTENDANCE_REGULARIZATION,
                        'priority': 100,
                        'is_active': True,
                    }
                ],
                'stages': [
                    {
                        'name': 'Manager review',
                        'sequence': 1,
                        'mode': 'ALL',
                        'fallback_type': 'PRIMARY_ORG_ADMIN',
                        'approvers': [{'approver_type': 'REPORTING_MANAGER'}],
                    }
                ],
            },
            format='json',
        )

        assert response.status_code == 201
        assert response.data['default_request_kind'] == ApprovalRequestKind.ATTENDANCE_REGULARIZATION

    def test_create_accepts_payroll_processing_defaults(self, org_admin_client):
        client, organisation = org_admin_client

        response = client.post(
            '/api/v1/org/approvals/workflows/',
            {
                'name': 'Payroll Workflow',
                'description': '',
                'is_default': True,
                'default_request_kind': ApprovalRequestKind.PAYROLL_PROCESSING,
                'is_active': True,
                'rules': [
                    {
                        'name': 'Default payroll rule',
                        'request_kind': ApprovalRequestKind.PAYROLL_PROCESSING,
                        'priority': 100,
                        'is_active': True,
                    }
                ],
                'stages': [
                    {
                        'name': 'Primary admin review',
                        'sequence': 1,
                        'mode': 'ALL',
                        'fallback_type': 'NONE',
                        'approvers': [{'approver_type': 'PRIMARY_ORG_ADMIN'}],
                    }
                ],
            },
            format='json',
        )

        assert response.status_code == 201
        assert response.data['default_request_kind'] == ApprovalRequestKind.PAYROLL_PROCESSING

    def test_catalog_readiness_and_simulation_cover_all_request_kinds(self, org_admin_client):
        client, organisation = org_admin_client
        manager_user = User.objects.create_user(
            email='simulation-manager@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        employee_user = User.objects.create_user(
            email='simulation-employee@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        manager = Employee.objects.create(
            organisation=organisation,
            user=manager_user,
            employee_code='EMP-SIM-MGR',
            status=EmployeeStatus.ACTIVE,
        )
        employee = Employee.objects.create(
            organisation=organisation,
            user=employee_user,
            employee_code='EMP-SIM',
            reporting_to=manager,
            status=EmployeeStatus.ACTIVE,
        )
        workflow = ApprovalWorkflow.objects.create(
            organisation=organisation,
            name='Default salary revision',
            is_default=True,
            default_request_kind=ApprovalRequestKind.SALARY_REVISION,
            is_active=True,
        )
        stage = ApprovalStage.objects.create(
            workflow=workflow,
            name='Manager review',
            sequence=1,
            fallback_type=ApprovalFallbackType.PRIMARY_ORG_ADMIN,
        )
        ApprovalStageApprover.objects.create(
            stage=stage,
            approver_type=ApprovalApproverType.REPORTING_MANAGER,
        )

        catalog_response = client.get('/api/v1/org/approvals/workflows/catalog/')
        readiness_response = client.get('/api/v1/org/approvals/workflows/readiness/')
        simulation_response = client.post(
            '/api/v1/org/approvals/workflows/simulate/',
            {
                'employee_id': str(employee.id),
                'request_kind': ApprovalRequestKind.SALARY_REVISION,
                'amount': '120000.00',
            },
            format='json',
        )

        assert catalog_response.status_code == 200
        request_kinds = {item['kind'] for item in catalog_response.data['request_kinds']}
        assert ApprovalRequestKind.PROMOTION in request_kinds
        assert ApprovalRequestKind.TRANSFER in request_kinds
        assert ApprovalApproverType.FINANCE_APPROVER in catalog_response.data['approver_types']
        assert readiness_response.status_code == 200
        assert len(readiness_response.data) == 9
        assert simulation_response.status_code == 200
        assert simulation_response.data['workflow_id'] == str(workflow.id)
        assert simulation_response.data['source'] == 'DEFAULT'
        assert simulation_response.data['stages'][0]['approvers'][0]['employee_id'] == str(manager.id)

    def test_create_accepts_stage_sla_fields(self, org_admin_client):
        client, organisation = org_admin_client
        approver_user = User.objects.create_user(
            email='sla-approver@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        approver = Employee.objects.create(
            organisation=organisation,
            user=approver_user,
            employee_code='EMP-SLA',
            status=EmployeeStatus.ACTIVE,
        )

        response = client.post(
            '/api/v1/org/approvals/workflows/',
            {
                'name': 'SLA Workflow',
                'description': '',
                'is_default': True,
                'default_request_kind': ApprovalRequestKind.LEAVE,
                'is_active': True,
                'rules': [
                    {
                        'name': 'Default leave rule',
                        'request_kind': ApprovalRequestKind.LEAVE,
                        'priority': 100,
                        'is_active': True,
                    }
                ],
                'stages': [
                    {
                        'name': 'Manager review',
                        'sequence': 1,
                        'mode': 'ALL',
                        'fallback_type': 'PRIMARY_ORG_ADMIN',
                        'reminder_after_hours': 24,
                        'escalate_after_hours': 48,
                        'escalation_target_type': 'SPECIFIC_EMPLOYEE',
                        'escalation_employee_id': str(approver.id),
                        'approvers': [{'approver_type': 'PRIMARY_ORG_ADMIN'}],
                    }
                ],
            },
            format='json',
        )

        assert response.status_code == 201
        assert response.data['stages'][0]['reminder_after_hours'] == 24
        assert response.data['stages'][0]['escalate_after_hours'] == 48
        assert response.data['stages'][0]['escalation_employee_id'] == str(approver.id)

    def test_can_create_approval_delegation(self, org_admin_client):
        client, organisation = org_admin_client
        delegator_user = User.objects.create_user(
            email='delegator@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        delegate_user = User.objects.create_user(
            email='delegate-api@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        delegator = Employee.objects.create(
            organisation=organisation,
            user=delegator_user,
            employee_code='EMP-D1',
            status=EmployeeStatus.ACTIVE,
        )
        delegate = Employee.objects.create(
            organisation=organisation,
            user=delegate_user,
            employee_code='EMP-D2',
            status=EmployeeStatus.ACTIVE,
        )

        response = client.post(
            '/api/v1/org/approvals/delegations/',
            {
                'delegator_employee_id': str(delegator.id),
                'delegate_employee_id': str(delegate.id),
                'request_kinds': [ApprovalRequestKind.LEAVE, ApprovalRequestKind.ON_DUTY],
                'start_date': '2026-04-01',
                'end_date': '2026-04-30',
                'is_active': True,
            },
            format='json',
        )

        assert response.status_code == 201
        assert ApprovalDelegation.objects.count() == 1
        assert response.data['delegator_employee_name'] == delegator.user.full_name

    def test_workflow_list_detail_and_patch_cover_success_and_validation(self, org_admin_client):
        client, organisation = org_admin_client
        workflow = ApprovalWorkflow.objects.create(
            organisation=organisation,
            name='Existing Workflow',
            is_default=True,
            default_request_kind=ApprovalRequestKind.LEAVE,
            is_active=True,
        )
        stage = ApprovalStage.objects.create(workflow=workflow, name='Manager review', sequence=1)
        ApprovalStageApprover.objects.create(stage=stage, approver_type='PRIMARY_ORG_ADMIN')

        list_response = client.get('/api/v1/org/approvals/workflows/')
        detail_response = client.get(f'/api/v1/org/approvals/workflows/{workflow.id}/')
        invalid_patch = client.patch(
            f'/api/v1/org/approvals/workflows/{workflow.id}/',
            {
                'name': 'Existing Workflow',
                'description': '',
                'is_default': True,
                'default_request_kind': ApprovalRequestKind.LEAVE,
                'is_active': True,
                'rules': [],
                'stages': [
                    {
                        'id': str(stage.id),
                        'name': 'Manager review',
                        'sequence': 1,
                        'mode': 'ALL',
                        'fallback_type': 'SPECIFIC_EMPLOYEE',
                        'fallback_employee_id': None,
                        'approvers': [{'approver_type': 'PRIMARY_ORG_ADMIN'}],
                    }
                ],
            },
            format='json',
        )
        valid_patch = client.patch(
            f'/api/v1/org/approvals/workflows/{workflow.id}/',
            {
                'name': 'Existing Workflow Updated',
                'description': '',
                'is_default': True,
                'default_request_kind': ApprovalRequestKind.LEAVE,
                'is_active': True,
                'rules': [],
                'stages': [
                    {
                        'id': str(stage.id),
                        'name': 'Manager review',
                        'sequence': 1,
                        'mode': 'ALL',
                        'fallback_type': 'PRIMARY_ORG_ADMIN',
                        'approvers': [{'approver_type': 'PRIMARY_ORG_ADMIN'}],
                    }
                ],
            },
            format='json',
        )

        assert list_response.status_code == 200
        assert detail_response.status_code == 200
        assert invalid_patch.status_code == 400
        assert 'fallback employee is required' in invalid_patch.data['error'].lower()
        assert valid_patch.status_code == 200
        assert valid_patch.data['name'] == 'Existing Workflow Updated'

    def test_org_inbox_delegation_list_and_org_action_endpoints(self, org_admin_client):
        client, organisation = org_admin_client
        requester_user = User.objects.create_user(
            email='requester-view@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        delegate_user = User.objects.create_user(
            email='delegate-view@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        requester = Employee.objects.create(
            organisation=organisation,
            user=requester_user,
            employee_code='EMP-REQ',
            status=EmployeeStatus.ACTIVE,
        )
        delegate = Employee.objects.create(
            organisation=organisation,
            user=delegate_user,
            employee_code='EMP-DEL',
            status=EmployeeStatus.ACTIVE,
        )
        admin_user = User.objects.get(email='admin@test.com')
        delegation = ApprovalDelegation.objects.create(
            organisation=organisation,
            delegator_employee=requester,
            delegate_employee=delegate,
            request_kinds=[ApprovalRequestKind.LEAVE],
            start_date=timezone.localdate(),
            is_active=True,
        )
        owned_action = _create_pending_action(
            organisation=organisation,
            requester=requester,
            approver_user=admin_user,
            subject=requester,
            request_kind=ApprovalRequestKind.LEAVE,
            subject_label='Owned leave',
        )
        other_action = _create_pending_action(
            organisation=organisation,
            requester=requester,
            approver_user=delegate.user,
            subject=requester,
            request_kind=ApprovalRequestKind.ON_DUTY,
            subject_label='Delegated OD',
        )

        inbox_response = client.get('/api/v1/org/approvals/inbox/')
        delegation_list = client.get('/api/v1/org/approvals/delegations/')
        delegation_patch = client.patch(
            f'/api/v1/org/approvals/delegations/{delegation.id}/',
            {
                'delegator_employee_id': str(requester.id),
                'delegate_employee_id': str(delegate.id),
                'request_kinds': [ApprovalRequestKind.LEAVE],
                'start_date': str(timezone.localdate()),
                'end_date': None,
                'is_active': False,
            },
            format='json',
        )

        with patch('apps.notifications.tasks.send_approval_outcome_email.delay'):
            approve_response = client.post(
                f'/api/v1/org/approvals/actions/{owned_action.id}/approve/',
                {'comment': 'Approved'},
                format='json',
            )
        reject_validation = client.post(
            f'/api/v1/org/approvals/actions/{other_action.id}/reject/',
            {'comment': ''},
            format='json',
        )

        assert inbox_response.status_code == 200
        assert len(inbox_response.data) == 1
        assert delegation_list.status_code == 200
        assert len(delegation_list.data) == 1
        assert delegation_patch.status_code == 200
        assert delegation_patch.data['is_active'] is False
        assert approve_response.status_code == 200
        assert reject_validation.status_code == 400
        assert 'comment' in reject_validation.data

    def test_employee_inbox_and_employee_approve_endpoint(self, employee_client):
        client, organisation, employee = employee_client
        approval_action = _create_pending_action(
            organisation=organisation,
            requester=employee,
            approver_user=employee.user,
            subject=employee,
            request_kind=ApprovalRequestKind.LEAVE,
            subject_label='My leave',
        )

        inbox_response = client.get('/api/v1/me/approvals/inbox/')
        with patch('apps.accounts.permissions.get_org_operations_guard', return_value={'approval_actions_blocked': False, 'reason': ''}):
            with patch('apps.notifications.tasks.send_approval_outcome_email.delay'):
                approve_response = client.post(
                    f'/api/v1/me/approvals/actions/{approval_action.id}/approve/',
                    {'comment': 'Looks good'},
                    format='json',
                )

        assert inbox_response.status_code == 200
        assert len(inbox_response.data) == 1
        assert approve_response.status_code == 200
        approval_action.refresh_from_db()
        assert approval_action.status == ApprovalActionStatus.APPROVED

    def test_employee_reject_endpoint(self, employee_client):
        client, organisation, employee = employee_client
        rejected_action = _create_pending_action(
            organisation=organisation,
            requester=employee,
            approver_user=employee.user,
            subject=employee,
            request_kind=ApprovalRequestKind.ON_DUTY,
            subject_label='My on duty',
        )

        with patch('apps.accounts.permissions.get_org_operations_guard', return_value={'approval_actions_blocked': False, 'reason': ''}):
            with patch('apps.notifications.tasks.send_approval_outcome_email.delay'):
                reject_response = client.post(
                    f'/api/v1/me/approvals/actions/{rejected_action.id}/reject/',
                    {'comment': 'Needs changes'},
                    format='json',
                )

        assert reject_response.status_code == 200
        rejected_action.refresh_from_db()
        assert rejected_action.status == ApprovalActionStatus.REJECTED
