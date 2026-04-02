from datetime import date
from decimal import Decimal

import pytest

from apps.accounts.models import AccountType, User, UserRole
from apps.approvals.models import (
    ApprovalApproverType,
    ApprovalRequestKind,
    ApprovalStage,
    ApprovalStageApprover,
    ApprovalWorkflow,
    ApprovalWorkflowRule,
)
from apps.approvals.services import approve_action
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
from apps.payroll.models import (
    CompensationAssignmentStatus,
    PayrollComponentType,
    PayrollRunStatus,
    PayrollTaxSlabSet,
    Payslip,
)
from apps.payroll.services import (
    assign_employee_compensation,
    calculate_pay_run,
    create_compensation_template,
    create_payroll_run,
    create_tax_slab_set,
    ensure_org_payroll_setup,
    finalize_pay_run,
    submit_compensation_assignment_for_approval,
    submit_pay_run_for_approval,
)


def _create_active_organisation(name='Acme Corp'):
    organisation = Organisation.objects.create(
        name=name,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    batch = create_licence_batch(
        organisation,
        quantity=25,
        price_per_licence_per_month='99.00',
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
    )
    mark_licence_batch_paid(batch, paid_at=date(2026, 4, 1))
    return organisation


def _approve_assignment_for_employee(employee, template, *, requester_user, requester_employee, approver_user):
    assignment = assign_employee_compensation(
        employee,
        template,
        effective_from=date(2026, 4, 1),
        actor=requester_user,
    )
    submit_compensation_assignment_for_approval(
        assignment,
        requester_user=requester_user,
        requester_employee=requester_employee,
    )
    approve_action(assignment.approval_run.actions.get(), approver_user)
    assignment.refresh_from_db()
    return assignment


def _create_workforce_user(email, *, role=UserRole.EMPLOYEE, organisation=None):
    return User.objects.create_user(
        email=email,
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=role,
        organisation=organisation,
        is_active=True,
    )


@pytest.mark.django_db
class TestPayrollServices:
    def test_ensure_org_payroll_setup_clones_active_ct_master(self):
        ct_user = User.objects.create_user(
            email='ct@test.com',
            password='pass123!',
            account_type=AccountType.CONTROL_TOWER,
            role=UserRole.CONTROL_TOWER,
            is_active=True,
        )
        organisation = _create_active_organisation()

        master = create_tax_slab_set(
            fiscal_year='2026-2027',
            name='FY 2026 Master',
            country_code='IN',
            slabs=[
                {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
                {'min_income': '300000', 'max_income': '700000', 'rate_percent': '10'},
                {'min_income': '700000', 'max_income': None, 'rate_percent': '20'},
            ],
            actor=ct_user,
        )

        setup = ensure_org_payroll_setup(organisation, actor=ct_user)

        org_set = PayrollTaxSlabSet.objects.get(organisation=organisation, is_active=True)
        assert org_set.source_set == master
        assert org_set.slabs.count() == 3
        assert setup['components']
        assert setup['tax_slab_set'] == org_set

    def test_pay_run_approval_and_finalize_generates_payslip(self):
        organisation = _create_active_organisation('Payroll Org')
        requester_user = _create_workforce_user('payroll-admin@test.com', role=UserRole.ORG_ADMIN, organisation=organisation)
        requester_employee = Employee.objects.create(
            organisation=organisation,
            user=requester_user,
            employee_code='EMP001',
            designation='Payroll Specialist',
            status=EmployeeStatus.ACTIVE,
        )
        approver_user = _create_workforce_user('finance-approver@test.com', role=UserRole.ORG_ADMIN, organisation=organisation)
        OrganisationMembership.objects.create(
            user=approver_user,
            organisation=organisation,
            is_org_admin=True,
            status=OrganisationMembershipStatus.ACTIVE,
        )
        approver_employee = Employee.objects.create(
            organisation=organisation,
            user=approver_user,
            employee_code='EMP002',
            designation='Finance Controller',
            status=EmployeeStatus.ACTIVE,
        )
        employee_user = _create_workforce_user('employee@test.com', organisation=organisation)
        employee = Employee.objects.create(
            organisation=organisation,
            user=employee_user,
            employee_code='EMP003',
            designation='Engineer',
            status=EmployeeStatus.ACTIVE,
            date_of_joining=date(2026, 4, 1),
        )
        OrganisationMembership.objects.create(
            user=requester_user,
            organisation=organisation,
            is_org_admin=True,
            status=OrganisationMembershipStatus.ACTIVE,
        )

        create_tax_slab_set(
            fiscal_year='2026-2027',
            name='FY 2026 Master',
            country_code='IN',
            slabs=[
                {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
                {'min_income': '300000', 'max_income': '700000', 'rate_percent': '10'},
                {'min_income': '700000', 'max_income': None, 'rate_percent': '20'},
            ],
            actor=requester_user,
        )
        ensure_org_payroll_setup(organisation, actor=requester_user)

        for request_kind in (
            ApprovalRequestKind.PAYROLL_PROCESSING,
            ApprovalRequestKind.SALARY_REVISION,
            ApprovalRequestKind.COMPENSATION_TEMPLATE_CHANGE,
        ):
            workflow = ApprovalWorkflow.objects.create(
                organisation=organisation,
                name=f'{request_kind.title()} Workflow',
                is_default=True,
                default_request_kind=request_kind,
                is_active=True,
            )
            ApprovalWorkflowRule.objects.create(
                workflow=workflow,
                name=f'{request_kind.title()} Rule',
                request_kind=request_kind,
                priority=100,
                is_active=True,
            )
            stage = ApprovalStage.objects.create(
                workflow=workflow,
                name='Finance review',
                sequence=1,
            )
            ApprovalStageApprover.objects.create(
                stage=stage,
                approver_type=ApprovalApproverType.SPECIFIC_EMPLOYEE,
                approver_employee=approver_employee,
            )

        template = create_compensation_template(
            organisation,
            name='Standard Monthly',
            description='Core salaried template',
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': PayrollComponentType.EARNING,
                    'monthly_amount': '50000',
                    'is_taxable': True,
                },
                {
                    'component_code': 'PF_EMPLOYEE',
                    'name': 'Employee PF',
                    'component_type': PayrollComponentType.EMPLOYEE_DEDUCTION,
                    'monthly_amount': '1800',
                    'is_taxable': False,
                },
            ],
            actor=requester_user,
        )
        _approve_assignment_for_employee(
            requester_employee,
            template,
            requester_user=requester_user,
            requester_employee=requester_employee,
            approver_user=approver_user,
        )
        _approve_assignment_for_employee(
            approver_employee,
            template,
            requester_user=requester_user,
            requester_employee=requester_employee,
            approver_user=approver_user,
        )
        assignment = _approve_assignment_for_employee(
            employee,
            template,
            requester_user=requester_user,
            requester_employee=requester_employee,
            approver_user=approver_user,
        )

        assert assignment.status == CompensationAssignmentStatus.APPROVED

        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            actor=requester_user,
            requester_user=requester_user,
            requester_employee=requester_employee,
        )
        calculate_pay_run(pay_run, actor=requester_user)
        pay_run.refresh_from_db()

        assert pay_run.status == PayrollRunStatus.CALCULATED
        assert pay_run.items.filter(status='READY').count() == 3
        item = pay_run.items.get(employee=employee)
        assert item.gross_pay == Decimal('50000.00')
        assert item.total_deductions > Decimal('1800.00')
        assert item.net_pay < item.gross_pay
        assert pay_run.use_attendance_inputs is False
        assert pay_run.attendance_snapshot['attendance_source'] == 'not_applied'
        assert pay_run.attendance_snapshot['period_start'] == '2026-04-01'
        assert pay_run.attendance_snapshot['period_end'] == '2026-04-30'
        assert pay_run.attendance_snapshot['employee_count'] == 3
        employee_attendance = next(
            entry
            for entry in pay_run.attendance_snapshot['employees']
            if entry['employee_id'] == str(employee.id)
        )
        assert employee_attendance['attendance_paid_days'] == item.snapshot['attendance']['attendance_paid_days']
        assert item.snapshot['attendance']['period_start'] == '2026-04-01'
        assert item.snapshot['attendance']['period_end'] == '2026-04-30'
        assert item.snapshot['attendance']['attendance_source'] == 'not_applied'
        assert Decimal(item.snapshot['lop_deduction']) == Decimal('0.00')

        submit_pay_run_for_approval(pay_run, requester_user=requester_user, requester_employee=requester_employee)
        approve_action(pay_run.approval_run.actions.get(), approver_user)
        pay_run.refresh_from_db()
        finalize_pay_run(pay_run, actor=requester_user)
        pay_run.refresh_from_db()

        assert pay_run.status == PayrollRunStatus.FINALIZED
        payslip = Payslip.objects.get(employee=employee, pay_run=pay_run)
        assert payslip.snapshot['employee_id'] == str(employee.id)
        assert Decimal(payslip.snapshot['net_pay']) == item.net_pay

    def test_pay_run_with_exception_items_cannot_be_submitted_or_finalized(self):
        organisation = _create_active_organisation('Exception Org')
        requester_user = _create_workforce_user('exception-admin@test.com', role=UserRole.ORG_ADMIN, organisation=organisation)
        requester_employee = Employee.objects.create(
            organisation=organisation,
            user=requester_user,
            employee_code='EMP100',
            designation='Payroll Admin',
            status=EmployeeStatus.ACTIVE,
        )
        affected_user = _create_workforce_user('missing-comp@test.com', organisation=organisation)
        Employee.objects.create(
            organisation=organisation,
            user=affected_user,
            employee_code='EMP101',
            designation='Analyst',
            status=EmployeeStatus.ACTIVE,
            date_of_joining=date(2026, 4, 1),
        )
        OrganisationMembership.objects.create(
            user=requester_user,
            organisation=organisation,
            is_org_admin=True,
            status=OrganisationMembershipStatus.ACTIVE,
        )

        create_tax_slab_set(
            fiscal_year='2026-2027',
            name='FY 2026 Master',
            country_code='IN',
            slabs=[
                {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
                {'min_income': '300000', 'max_income': '700000', 'rate_percent': '10'},
                {'min_income': '700000', 'max_income': None, 'rate_percent': '20'},
            ],
            actor=requester_user,
        )
        ensure_org_payroll_setup(organisation, actor=requester_user)

        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            actor=requester_user,
            requester_user=requester_user,
            requester_employee=requester_employee,
        )
        calculate_pay_run(pay_run, actor=requester_user)
        pay_run.refresh_from_db()

        assert pay_run.items.filter(status='EXCEPTION').count() == 2

        with pytest.raises(ValueError) as submit_exc:
            submit_pay_run_for_approval(pay_run, requester_user=requester_user, requester_employee=requester_employee)
        assert 'Resolve payroll exceptions before proceeding' in str(submit_exc.value)

        with pytest.raises(ValueError) as finalize_exc:
            finalize_pay_run(pay_run, actor=requester_user, skip_approval=True)
        assert 'Resolve payroll exceptions before proceeding' in str(finalize_exc.value)
