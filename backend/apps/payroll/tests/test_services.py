from datetime import date
from decimal import Decimal
from unittest.mock import patch

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
from apps.notifications.models import Notification, NotificationKind
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
    InvestmentDeclaration,
    InvestmentSection,
    PayrollComponentType,
    PayrollRunStatus,
    PayrollTaxSlabSet,
    Payslip,
    TaxRegime,
)
from apps.payroll.services import (
    _months_remaining_in_fiscal_year,
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

from .test_service_setup import _attach_registered_and_billing_addresses


def _create_active_organisation(name='Acme Corp'):
    organisation = Organisation.objects.create(
        name=name,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    _attach_registered_and_billing_addresses(organisation)
    batch = create_licence_batch(
        organisation,
        quantity=25,
        price_per_licence_per_month='99.00',
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
    )
    mark_licence_batch_paid(batch, paid_at=date(2026, 4, 1))
    return organisation


def _approve_assignment_for_employee(employee, template, *, requester_user, requester_employee, approver_user, tax_regime=TaxRegime.NEW):
    assignment = assign_employee_compensation(
        employee,
        template,
        effective_from=date(2026, 4, 1),
        actor=requester_user,
        tax_regime=tax_regime,
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
    def test_ensure_org_payroll_setup_provisions_components_without_org_slab_copy(self):
        ct_user = User.objects.create_user(
            email='ct@test.com',
            password='pass123!',
            account_type=AccountType.CONTROL_TOWER,
            role=UserRole.CONTROL_TOWER,
            is_active=True,
        )
        organisation = _create_active_organisation()

        create_tax_slab_set(
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

        # CT masters are used directly; no org-level copy is created.
        assert not PayrollTaxSlabSet.objects.filter(organisation=organisation).exists()
        assert 'tax_slab_set' not in setup
        assert setup['components']

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

    def test_pay_run_uses_old_regime_slab_set_for_old_regime_assignment(self):
        organisation = _create_active_organisation('Old Regime Org')
        requester_user = _create_workforce_user('old-regime-admin@test.com', role=UserRole.ORG_ADMIN, organisation=organisation)
        employee_user = _create_workforce_user('old-regime-employee@test.com', organisation=organisation)
        employee = Employee.objects.create(
            organisation=organisation,
            user=employee_user,
            employee_code='EMP200',
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
            name='FY 2026 New Regime',
            country_code='IN',
            slabs=[
                {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
                {'min_income': '300000', 'max_income': '700000', 'rate_percent': '5'},
                {'min_income': '700000', 'max_income': '1000000', 'rate_percent': '10'},
                {'min_income': '1000000', 'max_income': None, 'rate_percent': '20'},
            ],
            actor=requester_user,
            organisation=organisation,
            is_old_regime=False,
        )
        old_regime_set = create_tax_slab_set(
            fiscal_year='2026-2027',
            name='FY 2026 Old Regime',
            country_code='IN',
            slabs=[
                {'min_income': '0', 'max_income': '250000', 'rate_percent': '0'},
                {'min_income': '250000', 'max_income': '500000', 'rate_percent': '5'},
                {'min_income': '500000', 'max_income': '1000000', 'rate_percent': '20'},
                {'min_income': '1000000', 'max_income': None, 'rate_percent': '30'},
            ],
            actor=requester_user,
            organisation=organisation,
            is_old_regime=True,
        )

        template = create_compensation_template(
            organisation,
            name='Old Regime Template',
            description='Tax regime routing test',
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': PayrollComponentType.EARNING,
                    'monthly_amount': '60000',
                    'is_taxable': True,
                }
            ],
            actor=requester_user,
        )
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
            tax_regime=TaxRegime.OLD,
        )

        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            actor=requester_user,
            requester_user=requester_user,
        )
        calculate_pay_run(pay_run, actor=requester_user)
        item = pay_run.items.get(employee=employee)

        assert item.snapshot['tax_regime'] == TaxRegime.OLD
        assert item.snapshot['tax_slab_set_id'] == str(old_regime_set.id)

    def test_old_regime_pay_run_applies_investment_declarations_before_surcharge(self):
        organisation = _create_active_organisation('Old Regime Surcharge Org')
        requester_user = _create_workforce_user('old-surcharge-admin@test.com', role=UserRole.ORG_ADMIN, organisation=organisation)
        employee_user = _create_workforce_user('old-surcharge-employee@test.com', organisation=organisation)
        employee = Employee.objects.create(
            organisation=organisation,
            user=employee_user,
            employee_code='EMP201',
            designation='Director',
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
            name='FY 2026 New Regime',
            country_code='IN',
            slabs=[
                {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
                {'min_income': '300000', 'max_income': '700000', 'rate_percent': '5'},
                {'min_income': '700000', 'max_income': '1000000', 'rate_percent': '10'},
                {'min_income': '1000000', 'max_income': None, 'rate_percent': '20'},
            ],
            actor=requester_user,
            organisation=organisation,
            is_old_regime=False,
        )
        old_regime_set = create_tax_slab_set(
            fiscal_year='2026-2027',
            name='FY 2026 Old Regime',
            country_code='IN',
            slabs=[
                {'min_income': '0', 'max_income': '250000', 'rate_percent': '0'},
                {'min_income': '250000', 'max_income': '500000', 'rate_percent': '5'},
                {'min_income': '500000', 'max_income': '1000000', 'rate_percent': '20'},
                {'min_income': '1000000', 'max_income': None, 'rate_percent': '30'},
            ],
            actor=requester_user,
            organisation=organisation,
            is_old_regime=True,
        )

        template = create_compensation_template(
            organisation,
            name='Old Regime Surcharge Template',
            description='Old regime surcharge composition',
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': PayrollComponentType.EARNING,
                    'monthly_amount': '500000',
                    'is_taxable': True,
                }
            ],
            actor=requester_user,
        )
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
            tax_regime=TaxRegime.OLD,
        )
        InvestmentDeclaration.objects.create(
            employee=employee,
            fiscal_year='2026-2027',
            section=InvestmentSection.SECTION_80C,
            description='PPF',
            declared_amount=Decimal('150000.00'),
        )

        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            actor=requester_user,
            requester_user=requester_user,
        )
        calculate_pay_run(pay_run, actor=requester_user)
        item = pay_run.items.get(employee=employee)

        assert item.snapshot['tax_regime'] == TaxRegime.OLD
        assert item.snapshot['tax_slab_set_id'] == str(old_regime_set.id)
        assert Decimal(item.snapshot['annual_taxable_after_sd']) == Decimal('5775000.00')
        assert Decimal(item.snapshot['annual_investment_deductions']) == Decimal('150000.00')
        assert Decimal(item.snapshot['annual_tax_before_rebate']) == Decimal('1545000.00')
        assert Decimal(item.snapshot['annual_surcharge']) == Decimal('154500.00')
        assert Decimal(item.snapshot['annual_tax_before_cess']) == Decimal('1699500.00')
        assert Decimal(item.snapshot['annual_cess']) == Decimal('67980.00')
        assert Decimal(item.snapshot['annual_tax_total']) == Decimal('1767480.00')

    def test_get_employee_arrears_for_run_sums_only_unincluded_entries(self):
        from apps.payroll.models import Arrears
        from apps.payroll.services import get_employee_arrears_for_run

        organisation = _create_active_organisation('Arrears Lookup Org')
        requester_user = _create_workforce_user('arrears-lookup-admin@test.com', role=UserRole.ORG_ADMIN, organisation=organisation)
        employee_user = _create_workforce_user('arrears-lookup-employee@test.com', organisation=organisation)
        employee = Employee.objects.create(
            organisation=organisation,
            user=employee_user,
            employee_code='EMP300',
            designation='Analyst',
            status=EmployeeStatus.ACTIVE,
            date_of_joining=date(2026, 4, 1),
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            actor=requester_user,
            requester_user=requester_user,
        )
        Arrears.objects.create(
            employee=employee,
            pay_run=pay_run,
            for_period_year=2026,
            for_period_month=3,
            reason='Salary revision',
            amount=Decimal('5000.00'),
        )
        Arrears.objects.create(
            employee=employee,
            pay_run=pay_run,
            for_period_year=2026,
            for_period_month=2,
            reason='Prior payout',
            amount=Decimal('2000.00'),
            is_included_in_payslip=True,
        )

        result = get_employee_arrears_for_run(employee, pay_run)

        assert result == Decimal('5000.00')

    def test_pay_run_includes_arrears_and_marks_them_processed_on_finalize(self):
        from apps.payroll.models import Arrears

        organisation = _create_active_organisation('Arrears Payroll Org')
        requester_user = _create_workforce_user('arrears-admin@test.com', role=UserRole.ORG_ADMIN, organisation=organisation)
        employee_user = _create_workforce_user('arrears-employee@test.com', organisation=organisation)
        employee = Employee.objects.create(
            organisation=organisation,
            user=employee_user,
            employee_code='EMP301',
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
        template = create_compensation_template(
            organisation,
            name='Arrears Template',
            description='Arrears integration test',
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': PayrollComponentType.EARNING,
                    'monthly_amount': '50000',
                    'is_taxable': True,
                }
            ],
            actor=requester_user,
        )
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            actor=requester_user,
            requester_user=requester_user,
        )
        arrears = Arrears.objects.create(
            employee=employee,
            pay_run=pay_run,
            for_period_year=2026,
            for_period_month=3,
            reason='Salary revision',
            amount=Decimal('5000.00'),
        )

        calculate_pay_run(pay_run, actor=requester_user)
        pay_run.refresh_from_db()
        item = pay_run.items.get(employee=employee)

        assert item.gross_pay == Decimal('55000.00')
        assert Decimal(item.snapshot['arrears']) == Decimal('5000.00')

        finalize_pay_run(pay_run, actor=requester_user, skip_approval=True)
        arrears.refresh_from_db()

        assert arrears.is_included_in_payslip is True

    @patch('django.db.transaction.on_commit')
    def test_finalize_pay_run_notifies_employees_and_queues_email(self, mock_on_commit):
        mock_on_commit.side_effect = lambda callback: callback()
        organisation = _create_active_organisation('Payroll Notification Org')
        requester_user = _create_workforce_user('payroll-notify-admin@test.com', role=UserRole.ORG_ADMIN, organisation=organisation)
        employee_user = _create_workforce_user('payroll-notify-employee@test.com', organisation=organisation)
        employee = Employee.objects.create(
            organisation=organisation,
            user=employee_user,
            employee_code='EMP400',
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
        template = create_compensation_template(
            organisation,
            name='Notification Template',
            description='Payroll notification test',
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': PayrollComponentType.EARNING,
                    'monthly_amount': '50000',
                    'is_taxable': True,
                }
            ],
            actor=requester_user,
        )
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            actor=requester_user,
            requester_user=requester_user,
        )
        calculate_pay_run(pay_run, actor=requester_user)

        with patch('apps.notifications.tasks.send_payroll_ready_email.delay') as mock_delay:
            finalize_pay_run(pay_run, actor=requester_user, skip_approval=True)

        notification = Notification.objects.get(recipient=employee_user)
        assert notification.kind == NotificationKind.PAYROLL_FINALIZED
        assert notification.title == 'Your payslip for April 2026 is ready'
        assert notification.object_id == str(pay_run.id)
        mock_delay.assert_called_once()

    def test_pay_run_allocates_tds_across_remaining_months_in_fiscal_year(self):
        organisation = _create_active_organisation('Remaining Months Org')
        requester_user = _create_workforce_user('remaining-months-admin@test.com', role=UserRole.ORG_ADMIN, organisation=organisation)
        employee_user = _create_workforce_user('remaining-months-employee@test.com', organisation=organisation)
        employee = Employee.objects.create(
            organisation=organisation,
            user=employee_user,
            employee_code='EMP202',
            designation='Senior Analyst',
            status=EmployeeStatus.ACTIVE,
            date_of_joining=date(2026, 10, 1),
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
            organisation=None,
        )
        ensure_org_payroll_setup(organisation, actor=requester_user)
        template = create_compensation_template(
            organisation,
            name='Remaining Months Template',
            description='TDS divisor check',
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': PayrollComponentType.EARNING,
                    'monthly_amount': '200000',
                    'is_taxable': True,
                }
            ],
            actor=requester_user,
        )
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 10, 1),
            actor=requester_user,
            auto_approve=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=10,
            actor=requester_user,
            requester_user=requester_user,
        )

        calculate_pay_run(pay_run, actor=requester_user)

        item = pay_run.items.get(employee=employee)
        annual_tax_total = Decimal(item.snapshot['annual_tax_total'])
        assert Decimal(item.snapshot['annual_taxable_gross']) == Decimal('1200000.00')
        assert item.income_tax == (annual_tax_total / Decimal('6')).quantize(Decimal('0.01'))


class TestTdsMonthlyAllocation:
    """Unit tests for _months_remaining_in_fiscal_year (pure function, no DB needed)."""

    def test_april_returns_12_months_remaining(self):
        # April is month 4 — start of fiscal year, all 12 months remain
        assert _months_remaining_in_fiscal_year(4) == 12

    def test_october_returns_6_months_remaining(self):
        # October is month 10 — mid fiscal year, 6 months remain (Oct–Mar)
        assert _months_remaining_in_fiscal_year(10) == 6

    def test_february_returns_2_months_remaining(self):
        # February is month 2 — near end of fiscal year, Feb and Mar remain
        assert _months_remaining_in_fiscal_year(2) == 2

    def test_march_returns_1_month_remaining(self):
        # March is month 3 — last month of fiscal year, only Mar remains
        assert _months_remaining_in_fiscal_year(3) == 1
