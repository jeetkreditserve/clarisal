from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.approvals.models import ApprovalRequestKind
from apps.payroll.models import PayrollRunItemStatus, PayrollRunStatus, TaxRegime
from apps.payroll.services import (
    _create_payroll_approval_run,
    assign_employee_compensation,
    calculate_pay_run,
    create_compensation_template,
    create_payroll_run,
    create_tax_slab_set,
    ensure_org_payroll_setup,
)

from .test_service_setup import (
    _create_active_organisation,
    _create_employee,
    _create_workflow,
)


def _basic_template(organisation, actor, name='Run Calc Template', monthly_amount='30000'):
    return create_compensation_template(
        organisation,
        name=name,
        actor=actor,
        lines=[
            {
                'component_code': 'BASIC',
                'name': 'Basic Pay',
                'component_type': 'EARNING',
                'monthly_amount': monthly_amount,
                'is_taxable': True,
            },
        ],
    )


@pytest.mark.django_db
class TestPayrollRunCalculationService:
    def test_calculate_pay_run_rejects_approved_and_finalized_runs(self):
        organisation = _create_active_organisation('Run Status Guard Org')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'status-guard@test.com',
            employee_code='EMPRC1',
        )
        approved_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )
        approved_run.status = PayrollRunStatus.APPROVED
        approved_run.save(update_fields=['status'])

        with pytest.raises(ValueError):
            calculate_pay_run(approved_run, actor=requester_user)

        approved_run.status = PayrollRunStatus.FINALIZED
        approved_run.save(update_fields=['status'])
        with pytest.raises(ValueError):
            calculate_pay_run(approved_run, actor=requester_user)

    def test_calculate_pay_run_cancels_pending_approval_run_before_recalculation(self):
        organisation = _create_active_organisation('Run Approval Cancel Org')
        requester_user, requester_employee = _create_employee(
            organisation,
            'recalc-requester@test.com',
            employee_code='EMPRC2',
        )
        _approver_user, approver_employee = _create_employee(
            organisation,
            'recalc-approver@test.com',
            employee_code='EMPRC3',
        )
        _create_workflow(organisation, approver_employee, ApprovalRequestKind.PAYROLL_PROCESSING)
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )
        approval_run = _create_payroll_approval_run(
            pay_run,
            ApprovalRequestKind.PAYROLL_PROCESSING,
            organisation,
            requester_user,
            requester_employee=requester_employee,
            subject_label=pay_run.name,
        )
        pay_run.approval_run = approval_run
        pay_run.save(update_fields=['approval_run'])

        with patch('apps.payroll.services.cancel_approval_run') as mock_cancel:
            calculate_pay_run(pay_run, actor=requester_user)

        pay_run.refresh_from_db()
        mock_cancel.assert_called_once_with(approval_run, actor=requester_user, subject_status=None)
        assert pay_run.approval_run is None
        assert pay_run.status == PayrollRunStatus.CALCULATED

    def test_calculate_pay_run_creates_exception_for_old_regime_without_old_slab_set(self):
        organisation = _create_active_organisation('Old Regime Missing Slab Org')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'old-regime-requester@test.com',
            employee_code='EMPRC4',
        )
        _employee_user, employee = _create_employee(
            organisation,
            'old-regime-employee@test.com',
            role='EMPLOYEE',
            employee_code='EMPRC5',
        )
        create_tax_slab_set(
            fiscal_year='2026-2027',
            name='FY 2026 New Regime',
            country_code='IN',
            slabs=[
                {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
                {'min_income': '300000', 'max_income': None, 'rate_percent': '10'},
            ],
            organisation=organisation,
            actor=requester_user,
            is_old_regime=False,
        )
        template = _basic_template(organisation, requester_user, name='Old Regime Calc Template')
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
            requester_user=requester_user,
        )

        calculate_pay_run(pay_run, actor=requester_user)

        item = pay_run.items.get(employee=employee)
        assert item.status == PayrollRunItemStatus.EXCEPTION
        assert 'old tax slab set' in item.message.lower()
        assert item.snapshot['tax_regime'] == TaxRegime.OLD

    def test_calculate_pay_run_uses_attendance_inputs_for_lop_and_overtime(self):
        organisation = _create_active_organisation('Attendance Payroll Org')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'attendance-requester@test.com',
            employee_code='EMPRC6',
        )
        _employee_user, employee = _create_employee(
            organisation,
            'attendance-employee@test.com',
            role='EMPLOYEE',
            employee_code='EMPRC7',
        )
        create_tax_slab_set(
            fiscal_year='2026-2027',
            name='CT Master',
            country_code='IN',
            slabs=[
                {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
                {'min_income': '300000', 'max_income': None, 'rate_percent': '10'},
            ],
            organisation=None,
            actor=requester_user,
        )
        ensure_org_payroll_setup(organisation, actor=requester_user)
        template = _basic_template(organisation, requester_user, monthly_amount='30000')
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
            requester_user=requester_user,
            use_attendance_inputs=True,
        )

        with patch('apps.attendance.services.get_payroll_attendance_summary') as mock_summary:
            mock_summary.return_value = {
                'paid_fraction': Decimal('20.00'),
                'overtime_minutes': 45,
                'lop_days': Decimal('10.00'),
            }
            calculate_pay_run(pay_run, actor=requester_user)

        item = pay_run.items.get(employee=employee)
        assert item.status == PayrollRunItemStatus.READY
        assert item.snapshot['attendance']['attendance_source'] == 'attendance_service'
        assert item.snapshot['attendance']['attendance_paid_days'] == '20.00'
        assert item.snapshot['attendance']['effective_lop_days'] == '10.00'
        assert item.snapshot['attendance_overtime_minutes'] == 45
        assert Decimal(item.snapshot['lop_deduction']) == Decimal('10000.00')

    def test_calculate_pay_run_prorates_joining_and_exit_month(self):
        organisation = _create_active_organisation('Proration Org')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'proration-requester@test.com',
            employee_code='EMPRC8',
        )
        _joiner_user, joiner = _create_employee(
            organisation,
            'joiner@test.com',
            role='EMPLOYEE',
            employee_code='EMPRC9',
        )
        _exiter_user, exiter = _create_employee(
            organisation,
            'exiter@test.com',
            role='EMPLOYEE',
            employee_code='EMPRC10',
        )
        joiner.date_of_joining = date(2026, 4, 15)
        joiner.save(update_fields=['date_of_joining'])
        exiter.date_of_exit = date(2026, 4, 10)
        exiter.save(update_fields=['date_of_exit'])

        create_tax_slab_set(
            fiscal_year='2026-2027',
            name='CT Master',
            country_code='IN',
            slabs=[
                {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
                {'min_income': '300000', 'max_income': None, 'rate_percent': '10'},
            ],
            organisation=None,
            actor=requester_user,
        )
        ensure_org_payroll_setup(organisation, actor=requester_user)
        template = _basic_template(organisation, requester_user, name='Proration Template')
        for employee in (joiner, exiter):
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
            requester_user=requester_user,
        )

        calculate_pay_run(pay_run, actor=requester_user)

        joiner_item = pay_run.items.get(employee=joiner)
        exiter_item = pay_run.items.get(employee=exiter)
        assert joiner_item.snapshot['paid_days'] == 16
        assert joiner_item.gross_pay == Decimal('16000.00')
        assert exiter_item.snapshot['paid_days'] == 10
        assert exiter_item.gross_pay == Decimal('10000.00')
