from datetime import date
from decimal import Decimal

import pytest

from apps.accounts.models import AccountType, User, UserRole
from apps.approvals.models import (
    ApprovalApproverType,
    ApprovalRequestKind,
    ApprovalRunStatus,
    ApprovalStage,
    ApprovalStageApprover,
    ApprovalWorkflow,
    ApprovalWorkflowRule,
)
from apps.employees.models import Employee, EmployeeStatus
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationStatus,
)
from apps.organisations.services import create_licence_batch, mark_licence_batch_paid
from apps.payroll.models import (
    CompensationAssignmentStatus,
    CompensationTemplateStatus,
    InvestmentDeclaration,
    InvestmentSection,
    PayrollTaxSlabSet,
    TaxRegime,
)
from apps.payroll.services import (
    _create_payroll_approval_run,
    _ensure_global_default_tax_master,
    _get_active_tax_slab_set,
    _resolve_payroll_requester_context,
    assign_employee_compensation,
    calculate_taxable_income_with_investments,
    create_compensation_template,
    create_payroll_run,
    create_tax_slab_set,
    ensure_org_payroll_setup,
    get_effective_compensation_assignment,
    get_total_80c_deduction,
    submit_compensation_assignment_for_approval,
    submit_compensation_template_for_approval,
    update_compensation_template,
    update_tax_slab_set,
)


def _create_active_organisation(name='Payroll Setup Org'):
    organisation = Organisation.objects.create(
        name=name,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    batch = create_licence_batch(
        organisation,
        quantity=10,
        price_per_licence_per_month='99.00',
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
    )
    mark_licence_batch_paid(batch, paid_at=date(2026, 4, 1))
    return organisation


def _create_user(email, *, organisation=None, role=UserRole.ORG_ADMIN):
    return User.objects.create_user(
        email=email,
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=role,
        organisation=organisation,
        is_active=True,
    )


def _create_employee(organisation, email, *, role=UserRole.EMPLOYEE, employee_code='EMP001'):
    user = _create_user(email, organisation=organisation, role=role)
    employee = Employee.objects.create(
        organisation=organisation,
        user=user,
        employee_code=employee_code,
        designation='Analyst',
        status=EmployeeStatus.ACTIVE,
        date_of_joining=date(2026, 4, 1),
    )
    return user, employee


def _slabs():
    return [
        {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
        {'min_income': '300000', 'max_income': '700000', 'rate_percent': '5'},
        {'min_income': '700000', 'max_income': None, 'rate_percent': '10'},
    ]


def _create_workflow(organisation, approver_employee, request_kind):
    workflow = ApprovalWorkflow.objects.create(
        organisation=organisation,
        name=f'{request_kind} workflow',
        is_default=True,
        default_request_kind=request_kind,
        is_active=True,
    )
    ApprovalWorkflowRule.objects.create(
        workflow=workflow,
        name=f'{request_kind} rule',
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
    return workflow


@pytest.mark.django_db
class TestPayrollServiceSetup:
    def test_ensure_global_default_tax_master_creates_missing_master(self):
        actor = User.objects.create_user(
            email='ct.master@test.com',
            password='pass123!',
            account_type=AccountType.CONTROL_TOWER,
            role=UserRole.CONTROL_TOWER,
            is_active=True,
        )

        tax_master = _ensure_global_default_tax_master(actor=actor)

        assert tax_master.organisation is None
        assert tax_master.is_system_master is True
        assert tax_master.is_old_regime is False
        assert tax_master.slabs.count() == 6

    def test_get_active_tax_slab_set_prefers_org_year_then_org_then_global(self):
        organisation = _create_active_organisation('Tax Resolution Org')
        global_other_year = create_tax_slab_set(
            fiscal_year='2025-2026',
            name='Global Old Year',
            country_code='IN',
            slabs=_slabs(),
            organisation=None,
        )
        global_same_year = create_tax_slab_set(
            fiscal_year='2026-2027',
            name='Global Same Year',
            country_code='IN',
            slabs=_slabs(),
            organisation=None,
        )
        org_other_year = create_tax_slab_set(
            fiscal_year='2025-2026',
            name='Org Old Year',
            country_code='IN',
            slabs=_slabs(),
            organisation=organisation,
        )
        org_same_year = create_tax_slab_set(
            fiscal_year='2026-2027',
            name='Org Same Year',
            country_code='IN',
            slabs=_slabs(),
            organisation=organisation,
        )

        assert _get_active_tax_slab_set(organisation, '2026-2027') == org_same_year

        org_same_year.is_active = False
        org_same_year.save(update_fields=['is_active'])
        assert _get_active_tax_slab_set(organisation, '2026-2027') == org_other_year

        org_other_year.is_active = False
        org_other_year.save(update_fields=['is_active'])
        assert _get_active_tax_slab_set(organisation, '2026-2027') == global_same_year

        global_same_year.is_active = False
        global_same_year.save(update_fields=['is_active'])
        assert _get_active_tax_slab_set(organisation, '2026-2027') == global_other_year

    def test_resolve_payroll_requester_context_prefers_employee_and_validates_missing_args(self):
        organisation = _create_active_organisation('Requester Context Org')
        requester_user, requester_employee = _create_employee(
            organisation,
            'requester@test.com',
            role=UserRole.ORG_ADMIN,
            employee_code='EMPREQ1',
        )

        resolved = _resolve_payroll_requester_context(
            requester_user=None,
            requester_employee=requester_employee,
            organisation=organisation,
        )

        assert resolved == (organisation, requester_user, requester_employee)

        with pytest.raises(ValueError):
            _resolve_payroll_requester_context(requester_user=None, requester_employee=None, organisation=None)

    def test_total_80c_deduction_and_old_regime_taxable_income_are_capped(self):
        organisation = _create_active_organisation('Investments Org')
        _user, employee = _create_employee(organisation, 'investments@test.com', employee_code='EMPINV1')
        InvestmentDeclaration.objects.create(
            employee=employee,
            fiscal_year='2026-2027',
            section=InvestmentSection.SECTION_80C,
            declared_amount=Decimal('200000.00'),
        )
        InvestmentDeclaration.objects.create(
            employee=employee,
            fiscal_year='2026-2027',
            section=InvestmentSection.SECTION_80D,
            declared_amount=Decimal('75000.00'),
        )

        assert get_total_80c_deduction(employee, '2026-2027') == Decimal('150000.00')
        assert calculate_taxable_income_with_investments(
            employee=employee,
            annual_gross=Decimal('1000000.00'),
            fiscal_year='2026-2027',
            tax_regime=TaxRegime.OLD,
        ) == Decimal('725000.00')
        assert calculate_taxable_income_with_investments(
            employee=employee,
            annual_gross=Decimal('1000000.00'),
            fiscal_year='2026-2027',
            tax_regime=TaxRegime.NEW,
        ) == Decimal('925000.00')

    def test_create_and_update_tax_slab_set_validate_and_replace_slabs(self):
        organisation = _create_active_organisation('Tax Update Org')

        with pytest.raises(ValueError):
            create_tax_slab_set(
                fiscal_year='2026-2027',
                name='Invalid',
                country_code='IN',
                slabs=[],
                organisation=organisation,
            )

        slab_set = create_tax_slab_set(
            fiscal_year='2026-2027',
            name='FY 2026',
            country_code='IN',
            slabs=_slabs(),
            organisation=organisation,
        )
        updated = update_tax_slab_set(
            slab_set,
            name='FY 2026 Old Regime',
            is_old_regime=True,
            slabs=[
                {'min_income': '0', 'max_income': '250000', 'rate_percent': '0'},
                {'min_income': '250000', 'max_income': None, 'rate_percent': '20'},
            ],
        )

        updated.refresh_from_db()
        assert updated.name == 'FY 2026 Old Regime'
        assert updated.is_old_regime is True
        assert list(updated.slabs.values_list('rate_percent', flat=True)) == [Decimal('0.00'), Decimal('20.00')]

    def test_create_and_update_compensation_template_manage_lines(self):
        organisation = _create_active_organisation('Template Org')
        actor, _actor_employee = _create_employee(
            organisation,
            'template-admin@test.com',
            role=UserRole.ORG_ADMIN,
            employee_code='EMPTPL1',
        )

        with pytest.raises(ValueError):
            create_compensation_template(
                organisation,
                name='Empty template',
                lines=[],
                actor=actor,
            )

        template = create_compensation_template(
            organisation,
            name='Standard Template',
            description='First version',
            actor=actor,
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': 'EARNING',
                    'monthly_amount': '30000',
                    'is_taxable': True,
                },
            ],
        )
        template.status = CompensationTemplateStatus.APPROVED
        template.save(update_fields=['status'])

        updated = update_compensation_template(
            template,
            name='Updated Template',
            description='Second version',
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': 'EARNING',
                    'monthly_amount': '35000',
                    'is_taxable': True,
                },
                {
                    'component_code': 'HRA',
                    'name': 'HRA',
                    'component_type': 'EARNING',
                    'monthly_amount': '15000',
                    'is_taxable': True,
                },
            ],
            actor=actor,
        )

        updated.refresh_from_db()
        assert updated.name == 'Updated Template'
        assert updated.description == 'Second version'
        assert updated.status == CompensationTemplateStatus.DRAFT
        assert updated.lines.count() == 2

    def test_submit_compensation_template_for_approval_creates_pending_run(self):
        organisation = _create_active_organisation('Template Approval Org')
        requester_user, requester_employee = _create_employee(
            organisation,
            'requester-template@test.com',
            role=UserRole.ORG_ADMIN,
            employee_code='EMPTA1',
        )
        _approver_user, approver_employee = _create_employee(
            organisation,
            'approver-template@test.com',
            role=UserRole.ORG_ADMIN,
            employee_code='EMPTA2',
        )
        _create_workflow(organisation, approver_employee, ApprovalRequestKind.COMPENSATION_TEMPLATE_CHANGE)
        template = create_compensation_template(
            organisation,
            name='Template For Approval',
            actor=requester_user,
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': 'EARNING',
                    'monthly_amount': '30000',
                    'is_taxable': True,
                },
            ],
        )

        result = submit_compensation_template_for_approval(
            template,
            requester_user=requester_user,
            requester_employee=requester_employee,
        )

        result.refresh_from_db()
        assert result.status == CompensationTemplateStatus.PENDING_APPROVAL
        assert result.approval_run.status == ApprovalRunStatus.PENDING
        assert result.approval_run.actions.count() == 1

    def test_assignment_submission_and_effective_assignment_resolution(self):
        organisation = _create_active_organisation('Assignment Approval Org')
        requester_user, requester_employee = _create_employee(
            organisation,
            'requester-assignment@test.com',
            role=UserRole.ORG_ADMIN,
            employee_code='EMPAS1',
        )
        _approver_user, approver_employee = _create_employee(
            organisation,
            'approver-assignment@test.com',
            role=UserRole.ORG_ADMIN,
            employee_code='EMPAS2',
        )
        employee_user, employee = _create_employee(
            organisation,
            'employee-assignment@test.com',
            role=UserRole.EMPLOYEE,
            employee_code='EMPAS3',
        )
        assert employee_user.organisation == organisation
        _create_workflow(organisation, approver_employee, ApprovalRequestKind.SALARY_REVISION)
        template = create_compensation_template(
            organisation,
            name='Assignment Template',
            actor=requester_user,
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': 'EARNING',
                    'monthly_amount': '30000',
                    'is_taxable': True,
                },
            ],
        )

        first_assignment = assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
        )
        second_assignment = assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 5, 1),
            actor=requester_user,
            auto_approve=False,
            tax_regime=TaxRegime.OLD,
        )
        submitted = submit_compensation_assignment_for_approval(
            second_assignment,
            requester_user=requester_user,
            requester_employee=requester_employee,
        )

        submitted.refresh_from_db()
        assert submitted.status == CompensationAssignmentStatus.PENDING_APPROVAL
        assert submitted.approval_run.actions.count() == 1
        assert get_effective_compensation_assignment(employee, date(2026, 4, 15)) == first_assignment
        assert get_effective_compensation_assignment(employee, date(2026, 5, 15)) == first_assignment

    def test_create_payroll_approval_run_requires_default_workflow_and_builds_action(self):
        organisation = _create_active_organisation('Payroll Approval Run Org')
        requester_user, requester_employee = _create_employee(
            organisation,
            'requester-run@test.com',
            role=UserRole.ORG_ADMIN,
            employee_code='EMPPR1',
        )
        _approver_user, approver_employee = _create_employee(
            organisation,
            'approver-run@test.com',
            role=UserRole.ORG_ADMIN,
            employee_code='EMPPR2',
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )

        with pytest.raises(ValueError):
            _create_payroll_approval_run(
                pay_run,
                ApprovalRequestKind.PAYROLL_PROCESSING,
                organisation,
                requester_user,
                requester_employee=requester_employee,
                subject_label=pay_run.name,
            )

        _create_workflow(organisation, approver_employee, ApprovalRequestKind.PAYROLL_PROCESSING)
        approval_run = _create_payroll_approval_run(
            pay_run,
            ApprovalRequestKind.PAYROLL_PROCESSING,
            organisation,
            requester_user,
            requester_employee=requester_employee,
            subject_label=pay_run.name,
        )

        assert approval_run.status == ApprovalRunStatus.PENDING
        assert approval_run.requested_by == requester_employee
        assert approval_run.actions.count() == 1

    def test_ensure_org_payroll_setup_clones_default_tax_master_once(self):
        organisation = _create_active_organisation('Org Setup Clone Org')
        actor = User.objects.create_user(
            email='ct-clone@test.com',
            password='pass123!',
            account_type=AccountType.CONTROL_TOWER,
            role=UserRole.CONTROL_TOWER,
            is_active=True,
        )
        master = create_tax_slab_set(
            fiscal_year='2026-2027',
            name='CT Master',
            country_code='IN',
            slabs=_slabs(),
            actor=actor,
            organisation=None,
        )

        first_setup = ensure_org_payroll_setup(organisation, actor=actor)
        second_setup = ensure_org_payroll_setup(organisation, actor=actor)

        assert first_setup['tax_slab_set'].source_set == master
        assert first_setup['tax_slab_set'].id == second_setup['tax_slab_set'].id
        assert PayrollTaxSlabSet.objects.filter(organisation=organisation, is_active=True).count() == 1
        assert len(first_setup['components']) == 8
