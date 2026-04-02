from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.accounts.models import User, UserRole
from apps.approvals.models import (
    ApprovalApproverType,
    ApprovalRequestKind,
    ApprovalStage,
    ApprovalStageApprover,
    ApprovalWorkflow,
    ApprovalWorkflowRule,
)
from apps.employees.models import Employee, EmployeeOffboardingProcess, OffboardingProcessStatus
from apps.employees.services import create_or_update_offboarding_process, invite_employee
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationStatus,
)
from apps.organisations.services import create_licence_batch, mark_licence_batch_paid


@pytest.fixture
def ct_user(db):
    return User.objects.create_superuser(
        email='ct@test.com',
        password='pass123!',
        role=UserRole.CONTROL_TOWER,
    )


@pytest.fixture
def org_admin(db):
    return User.objects.create_user(
        email='admin@test.com',
        password='pass123!',
        role=UserRole.ORG_ADMIN,
        is_active=True,
    )


@pytest.fixture
def organisation(ct_user):
    return Organisation.objects.create(
        name='Acme Corp',
        created_by=ct_user,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )


@pytest.fixture
def default_workflows(organisation, org_admin):
    leave_workflow = ApprovalWorkflow.objects.create(
        organisation=organisation,
        name='Default Leave Workflow',
        is_default=True,
        default_request_kind=ApprovalRequestKind.LEAVE,
        is_active=True,
        created_by=org_admin,
    )
    ApprovalWorkflowRule.objects.create(
        workflow=leave_workflow,
        name='Default Leave Rule',
        request_kind=ApprovalRequestKind.LEAVE,
        priority=100,
        is_active=True,
    )
    ApprovalStage.objects.create(
        workflow=leave_workflow,
        name='Primary Admin Approval',
        sequence=1,
    )

    on_duty_workflow = ApprovalWorkflow.objects.create(
        organisation=organisation,
        name='Default On-Duty Workflow',
        is_default=True,
        default_request_kind=ApprovalRequestKind.ON_DUTY,
        is_active=True,
        created_by=org_admin,
    )
    ApprovalWorkflowRule.objects.create(
        workflow=on_duty_workflow,
        name='Default OD Rule',
        request_kind=ApprovalRequestKind.ON_DUTY,
        priority=100,
        is_active=True,
    )
    ApprovalStage.objects.create(
        workflow=on_duty_workflow,
        name='Primary Admin Approval',
        sequence=1,
    )

    regularization_workflow = ApprovalWorkflow.objects.create(
        organisation=organisation,
        name='Default Attendance Regularization Workflow',
        is_default=True,
        default_request_kind=ApprovalRequestKind.ATTENDANCE_REGULARIZATION,
        is_active=True,
        created_by=org_admin,
    )
    ApprovalWorkflowRule.objects.create(
        workflow=regularization_workflow,
        name='Default Regularization Rule',
        request_kind=ApprovalRequestKind.ATTENDANCE_REGULARIZATION,
        priority=100,
        is_active=True,
    )
    stage = ApprovalStage.objects.create(
        workflow=regularization_workflow,
        name='Primary Admin Approval',
        sequence=1,
    )
    ApprovalStageApprover.objects.create(
        stage=stage,
        approver_type=ApprovalApproverType.PRIMARY_ORG_ADMIN,
    )
    organisation.primary_admin_user = org_admin
    organisation.save(update_fields=['primary_admin_user', 'modified_at'])
    return {
        'leave': leave_workflow,
        'on_duty': on_duty_workflow,
        'attendance_regularization': regularization_workflow,
    }


@pytest.mark.django_db
class TestInviteEmployee:
    @patch('apps.invitations.services.transaction.on_commit')
    def test_invite_blocks_when_active_paid_capacity_is_exhausted(self, mock_on_commit, organisation, org_admin, default_workflows):
        mock_on_commit.side_effect = lambda fn: None
        batch = create_licence_batch(
            organisation,
            quantity=1,
            price_per_licence_per_month=Decimal('100.00'),
            start_date=date(2026, 3, 1),
            end_date=date(2026, 12, 31),
            created_by=org_admin,
        )
        mark_licence_batch_paid(batch, paid_by=org_admin, paid_at=date(2026, 4, 1))

        invite_employee(
            organisation,
            company_email='employee1@test.com',
            first_name='One',
            last_name='Employee',
            invited_by=org_admin,
        )

        with pytest.raises(ValueError, match='No licences are available for this organisation.'):
            invite_employee(
                organisation,
                company_email='employee2@test.com',
                first_name='Two',
                last_name='Employee',
                invited_by=org_admin,
            )


@pytest.mark.django_db
class TestOffboardingProcess:
    def test_create_or_update_offboarding_process_seeds_default_tasks(self, organisation, org_admin, default_workflows):
        employee_user = User.objects.create_user(
            email='employee.offboarding@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        employee = Employee.objects.create(
            organisation=organisation,
            user=employee_user,
            status='ACTIVE',
            employee_code='EMP002',
        )

        process = create_or_update_offboarding_process(
            employee,
            exit_status='RESIGNED',
            date_of_exit=date(2026, 4, 30),
            exit_reason='Personal reason',
            exit_notes='Handover in progress',
            actor=org_admin,
        )

        assert process.status == OffboardingProcessStatus.IN_PROGRESS
        assert process.exit_reason == 'Personal reason'
        assert process.tasks.count() >= 6

        updated = create_or_update_offboarding_process(
            employee,
            exit_status='RESIGNED',
            date_of_exit=date(2026, 5, 2),
            exit_reason='Updated note',
            exit_notes='Final payroll review',
            actor=org_admin,
        )

        assert updated.id == process.id
        assert EmployeeOffboardingProcess.objects.count() == 1
        assert updated.date_of_exit == date(2026, 5, 2)
        assert updated.exit_notes == 'Final payroll review'
