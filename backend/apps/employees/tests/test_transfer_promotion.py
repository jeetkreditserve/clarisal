from datetime import date
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.approvals.models import ApprovalRequestKind, ApprovalRun, ApprovalRunStatus, ApprovalWorkflow
from apps.approvals.services import reject_action
from apps.departments.models import Department
from apps.employees.models import Designation, Employee, EmployeeStatus
from apps.employees.services import (
    apply_promotion_event,
    apply_transfer_event,
    approve_promotion_event,
    approve_transfer_event,
    create_promotion_event,
    create_transfer_event,
    get_employee_career_timeline,
)
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationStatus,
)
from apps.payroll.models import (
    CompensationAssignmentStatus,
    CompensationTemplate,
    CompensationTemplateLine,
    CompensationTemplateStatus,
    PayrollComponent,
    PayrollComponentType,
)
from apps.payroll.services import assign_employee_compensation


@pytest.fixture
def org_admin(db):
    return User.objects.create_user(
        email='admin@test.com',
        password='pass123!',
        role=UserRole.ORG_ADMIN,
        is_active=True,
    )


@pytest.fixture
def employee_user(db):
    return User.objects.create_user(
        email='john@org.com',
        password='pass123!',
        role=UserRole.EMPLOYEE,
        is_active=True,
    )


@pytest.fixture
def organisation(db, org_admin):
    return Organisation.objects.create(
        name='Test Org',
        created_by=org_admin,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )


@pytest.fixture
def department(db, organisation):
    return Department.objects.create(
        organisation=organisation,
        name='Engineering',
    )


@pytest.fixture
def department2(db, organisation):
    return Department.objects.create(
        organisation=organisation,
        name='Product',
    )


@pytest.fixture
def employee(db, organisation, employee_user, department):
    return Employee.objects.create(
        organisation=organisation,
        user=employee_user,
        employee_code='EMP001',
        department=department,
    )


@pytest.fixture
def designation_senior(db, organisation):
    return Designation.objects.create(
        organisation=organisation,
        name='Senior Engineer',
        level=3,
    )


@pytest.fixture
def designation_lead(db, organisation):
    return Designation.objects.create(
        organisation=organisation,
        name='Lead Engineer',
        level=4,
    )


class TestTransferEventService:
    def test_create_transfer_event(self, organisation, employee, department2, org_admin):
        transfer = create_transfer_event(
            employee=employee,
            to_department=department2,
            effective_date=date(2026, 5, 1),
            reason='Team restructure',
            requested_by=org_admin,
        )

        assert transfer.from_department == employee.department
        assert transfer.to_department == department2
        assert transfer.status == 'PENDING'

    def test_approve_transfer_event(self, organisation, employee, department2, org_admin):
        transfer = create_transfer_event(
            employee=employee,
            to_department=department2,
            effective_date=date(2026, 5, 1),
            requested_by=org_admin,
        )

        approved = approve_transfer_event(transfer, approved_by=org_admin, notes='Approved')

        assert approved.status == 'APPROVED'
        assert approved.approved_by == org_admin
        assert approved.approved_at is not None

    def test_apply_transfer_event(self, organisation, employee, department2, org_admin):
        transfer = create_transfer_event(
            employee=employee,
            to_department=department2,
            effective_date=date(2026, 1, 1),
            requested_by=org_admin,
        )
        approve_transfer_event(transfer, approved_by=org_admin)

        applied = apply_transfer_event(transfer, actor=org_admin)

        assert applied.status == 'EFFECTIVE'
        employee.refresh_from_db()
        assert employee.department == department2


class TestPromotionEventService:
    def test_create_promotion_event(self, organisation, employee, designation_lead, org_admin):
        promotion = create_promotion_event(
            employee=employee,
            to_designation=designation_lead,
            effective_date=date(2026, 6, 1),
            reason='Strong performance',
            requested_by=org_admin,
        )

        assert promotion.from_designation is None
        assert promotion.to_designation == designation_lead
        assert promotion.status == 'PENDING'

    def test_approve_promotion_event(self, organisation, employee, designation_lead, org_admin):
        promotion = create_promotion_event(
            employee=employee,
            to_designation=designation_lead,
            effective_date=date(2026, 6, 1),
            requested_by=org_admin,
        )

        approved = approve_promotion_event(promotion, approved_by=org_admin)

        assert approved.status == 'APPROVED'

    def test_apply_promotion_event(self, organisation, employee, designation_lead, org_admin):
        promotion = create_promotion_event(
            employee=employee,
            to_designation=designation_lead,
            effective_date=date(2026, 1, 1),
            requested_by=org_admin,
        )
        approve_promotion_event(promotion, approved_by=org_admin)

        applied = apply_promotion_event(promotion, actor=org_admin)

        assert applied.status == 'EFFECTIVE'
        employee.refresh_from_db()
        assert employee.designation == designation_lead.name


class TestCareerTimeline:
    def test_get_career_timeline_empty(self, organisation, employee):
        timeline = get_employee_career_timeline(employee)
        assert len(timeline) == 0

    def test_get_career_timeline_with_events(self, organisation, employee, department2, designation_lead, org_admin):
        transfer = create_transfer_event(
            employee=employee,
            to_department=department2,
            effective_date=date(2026, 3, 1),
            requested_by=org_admin,
        )
        approve_transfer_event(transfer, approved_by=org_admin)
        apply_transfer_event(transfer, actor=org_admin)

        create_promotion_event(
            employee=employee,
            to_designation=designation_lead,
            effective_date=date(2026, 6, 1),
            requested_by=org_admin,
        )

        timeline = get_employee_career_timeline(employee)

        assert len(timeline) == 2
        timeline_types = {t['type'] for t in timeline}
        assert 'TRANSFER' in timeline_types
        assert 'PROMOTION' in timeline_types

        transfer_item = next(t for t in timeline if t['type'] == 'TRANSFER')
        assert transfer_item['status'] == 'EFFECTIVE'
        assert transfer_item['to_department'] == 'Product'


@pytest.mark.django_db
class TestPromotionTriggersCompensationDraft:
    def test_apply_promotion_creates_compensation_assignment_draft(
        self,
        organisation,
        employee_user,
        department,
        designation_senior,
        designation_lead,
        org_admin,
    ):
        employee = Employee.objects.create(
            organisation=organisation,
            user=employee_user,
            employee_code="EMP002",
            department=department,
            designation=designation_senior.name,
            status=EmployeeStatus.ACTIVE,
        )
        employee_user.organisation = organisation
        employee_user.save(update_fields=["organisation"])

        basic = PayrollComponent.objects.create(
            organisation=organisation,
            name="Basic",
            code="BASIC",
            component_type=PayrollComponentType.EARNING,
            is_taxable=True,
        )
        template = CompensationTemplate.objects.create(
            organisation=organisation,
            name="Default Template",
            status=CompensationTemplateStatus.APPROVED,
        )

        CompensationTemplateLine.objects.create(
            template=template,
            component=basic,
            monthly_amount="20000.00",
            sequence=1,
        )

        assign_employee_compensation(
            employee=employee,
            template=template,
            effective_from=date(2026, 1, 1),
            actor=org_admin,
            auto_approve=True,
        )

        promotion_effective = timezone.now().date()
        promotion = create_promotion_event(
            employee=employee,
            to_designation=designation_lead,
            effective_date=promotion_effective,
            requested_by=org_admin,
        )
        approve_promotion_event(promotion, approved_by=org_admin)

        assert promotion.revised_compensation_assignment is None

        applied = apply_promotion_event(promotion, actor=org_admin)

        assert applied.status == "EFFECTIVE"
        assert applied.revised_compensation_assignment is not None
        assert (
            applied.revised_compensation_assignment.status
            == CompensationAssignmentStatus.DRAFT
        )
        assert applied.revised_compensation_assignment.effective_from == promotion_effective
        assert applied.revised_compensation_assignment.template == template
        assert applied.revised_compensation_assignment.lines.count() == 1

    def test_apply_promotion_links_existing_compensation_assignment(
        self,
        organisation,
        employee_user,
        department,
        designation_senior,
        designation_lead,
        org_admin,
    ):
        employee = Employee.objects.create(
            organisation=organisation,
            user=employee_user,
            employee_code="EMP003",
            department=department,
            designation=designation_senior.name,
            status=EmployeeStatus.ACTIVE,
        )

        basic = PayrollComponent.objects.create(
            organisation=organisation,
            name="Basic",
            code="BASIC",
            component_type=PayrollComponentType.EARNING,
            is_taxable=True,
        )
        template = CompensationTemplate.objects.create(
            organisation=organisation,
            name="Lead Template",
            status=CompensationTemplateStatus.APPROVED,
        )
        CompensationTemplateLine.objects.create(
            template=template,
            component=basic,
            monthly_amount="30000.00",
            sequence=1,
        )

        existing_assignment = assign_employee_compensation(
            employee=employee,
            template=template,
            effective_from=date(2026, 1, 1),
            actor=org_admin,
            auto_approve=True,
        )

        promotion_effective = timezone.now().date()
        promotion = create_promotion_event(
            employee=employee,
            to_designation=designation_lead,
            effective_date=promotion_effective,
            revised_compensation=existing_assignment,
            requested_by=org_admin,
        )
        approve_promotion_event(promotion, approved_by=org_admin)

        applied = apply_promotion_event(promotion, actor=org_admin)

        assert applied.revised_compensation_assignment == existing_assignment
        assert (
            applied.revised_compensation_assignment.status
            == CompensationAssignmentStatus.APPROVED
        )


@pytest.mark.django_db
class TestPromotionTransferApprovalWorkflowIntegration:
    def test_create_promotion_event_creates_approval_run(self, organisation, employee, designation_lead, org_admin):
        promotion = create_promotion_event(
            employee=employee,
            to_designation=designation_lead,
            effective_date=date(2026, 6, 1),
            reason='Strong performance',
            requested_by=org_admin,
        )

        approval_run = ApprovalRun.objects.filter(
            object_id=promotion.id,
            request_kind=ApprovalRequestKind.PROMOTION,
        ).first()
        assert approval_run is not None, "Approval run should be created for promotion"
        assert approval_run.status == ApprovalRunStatus.PENDING
        assert approval_run.requested_by == employee

    def test_create_transfer_event_creates_approval_run(self, organisation, employee, department2, org_admin):
        transfer = create_transfer_event(
            employee=employee,
            to_department=department2,
            effective_date=date(2026, 5, 1),
            reason='Team restructure',
            requested_by=org_admin,
        )

        approval_run = ApprovalRun.objects.filter(
            object_id=transfer.id,
            request_kind=ApprovalRequestKind.TRANSFER,
        ).first()
        assert approval_run is not None, "Approval run should be created for transfer"
        assert approval_run.status == ApprovalRunStatus.PENDING
        assert approval_run.requested_by == employee

    def test_promotion_auto_creates_default_workflow_when_none_exists(self, organisation, employee, designation_lead, org_admin):
        assert not ApprovalWorkflow.objects.filter(
            organisation=organisation,
            is_default=True,
            default_request_kind=ApprovalRequestKind.PROMOTION,
        ).exists()

        create_promotion_event(
            employee=employee,
            to_designation=designation_lead,
            effective_date=date(2026, 6, 1),
            reason='Strong performance',
            requested_by=org_admin,
        )

        workflow = ApprovalWorkflow.objects.get(
            organisation=organisation,
            is_default=True,
            default_request_kind=ApprovalRequestKind.PROMOTION,
        )
        assert workflow.is_active is True
        assert workflow.stages.count() == 1
        assert workflow.stages.first().sequence == 1

    def test_approval_run_rejection_updates_promotion_status(self, organisation, employee, designation_lead, org_admin):
        promotion = create_promotion_event(
            employee=employee,
            to_designation=designation_lead,
            effective_date=date(2026, 6, 1),
            reason='Strong performance',
            requested_by=org_admin,
        )

        approval_run = ApprovalRun.objects.get(
            object_id=promotion.id,
            request_kind=ApprovalRequestKind.PROMOTION,
        )
        action = approval_run.actions.first()
        with patch('apps.approvals.services.get_org_operations_guard',
                   return_value={'approval_actions_blocked': False, 'reason': ''}):
            reject_action(action, actor=org_admin, comment='Not approved')

        promotion.refresh_from_db()
        assert promotion.status == 'REJECTED'
        assert promotion.notes == 'Not approved'
