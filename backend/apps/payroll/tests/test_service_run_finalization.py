from decimal import Decimal

import pytest

from apps.approvals.models import ApprovalRequestKind
from apps.employees.models import EmployeeGovernmentId, GovernmentIdType
from apps.payroll.models import (
    PayrollRunItem,
    PayrollRunItemStatus,
    PayrollRunStatus,
    Payslip,
    TaxRegime,
)
from apps.payroll.services import (
    _create_payroll_approval_run,
    create_payroll_run,
    finalize_pay_run,
    generate_form16_data,
    rerun_payroll_run,
    submit_pay_run_for_approval,
)

from .test_service_setup import (
    _create_active_organisation,
    _create_employee,
    _create_workflow,
)


def _create_ready_item(pay_run, employee, *, gross='50000.00', net='45000.00', tax_regime=TaxRegime.NEW):
    return PayrollRunItem.objects.create(
        pay_run=pay_run,
        employee=employee,
        status=PayrollRunItemStatus.READY,
        gross_pay=Decimal(gross),
        employee_deductions=Decimal('3000.00'),
        employer_contributions=Decimal('3000.00'),
        income_tax=Decimal('2000.00'),
        total_deductions=Decimal('5000.00'),
        net_pay=Decimal(net),
        snapshot={
            'tax_regime': tax_regime,
            'annual_standard_deduction': '75000.00',
            'annual_taxable_after_sd': '525000.00',
            'annual_tax_before_rebate': '10000.00',
            'annual_rebate_87a': '0.00',
            'annual_cess': '400.00',
            'annual_tax_total': '10400.00',
            'gross_pay': gross,
            'income_tax': '2000.00',
            'esi_eligibility_mode': 'DIRECT',
            'esi_contribution_period_start': '2026-04-01',
            'esi_contribution_period_end': '2026-09-30',
            'lines': [],
        },
    )


@pytest.mark.django_db
class TestPayrollRunFinalizationService:
    def test_generate_form16_data_includes_pan_and_old_regime_flag(self):
        organisation = _create_active_organisation('Form16 Org')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'form16-requester@test.com',
            employee_code='EMPF16A',
        )
        _employee_user, employee = _create_employee(
            organisation,
            'form16-employee@test.com',
            role='EMPLOYEE',
            employee_code='EMPF16B',
        )
        EmployeeGovernmentId.objects.create(
            employee=employee,
            id_type=GovernmentIdType.PAN,
            masked_identifier='ABCDE1234F',
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )
        item = _create_ready_item(pay_run, employee, tax_regime=TaxRegime.OLD)
        Payslip.objects.create(
            organisation=organisation,
            employee=employee,
            pay_run=pay_run,
            pay_run_item=item,
            slip_number='202604-EMPF16B',
            period_year=2026,
            period_month=4,
            snapshot=item.snapshot,
            rendered_text='Rendered',
        )

        result = generate_form16_data(pay_run)

        assert result['fiscal_year'] == '2026-2027'
        assert result['employees'][0]['employee_pan'] == 'ABCDE1234F'
        assert result['employees'][0]['part_b']['opting_out_of_section_115bac_1a'] == 'YES'

    def test_submit_pay_run_for_approval_requires_calculated_status(self):
        organisation = _create_active_organisation('Submit Guard Org')
        requester_user, requester_employee = _create_employee(
            organisation,
            'submit-guard@test.com',
            employee_code='EMPF16C',
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )

        with pytest.raises(ValueError):
            submit_pay_run_for_approval(
                pay_run,
                requester_user=requester_user,
                requester_employee=requester_employee,
            )

    def test_submit_pay_run_for_approval_requires_ready_items(self):
        organisation = _create_active_organisation('Submit Ready Org')
        requester_user, requester_employee = _create_employee(
            organisation,
            'submit-ready@test.com',
            employee_code='EMPF16D',
        )
        _approver_user, approver_employee = _create_employee(
            organisation,
            'submit-ready-approver@test.com',
            employee_code='EMPF16E',
        )
        _create_workflow(organisation, approver_employee, ApprovalRequestKind.PAYROLL_PROCESSING)
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )
        pay_run.status = PayrollRunStatus.CALCULATED
        pay_run.save(update_fields=['status'])

        with pytest.raises(ValueError):
            submit_pay_run_for_approval(
                pay_run,
                requester_user=requester_user,
                requester_employee=requester_employee,
            )

    def test_finalize_pay_run_requires_approval_unless_skipped(self):
        organisation = _create_active_organisation('Finalize Guard Org')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'finalize-guard@test.com',
            employee_code='EMPF16F',
        )
        _employee_user, employee = _create_employee(
            organisation,
            'finalize-employee@test.com',
            role='EMPLOYEE',
            employee_code='EMPF16G',
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )
        _create_ready_item(pay_run, employee)
        pay_run.status = PayrollRunStatus.CALCULATED
        pay_run.save(update_fields=['status'])

        with pytest.raises(ValueError):
            finalize_pay_run(pay_run, actor=requester_user)

    def test_finalize_pay_run_persists_esi_contribution_period_fields(self):
        organisation = _create_active_organisation('Finalize ESI Org')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'finalize-esi-requester@test.com',
            employee_code='EMPF16K',
        )
        _employee_user, employee = _create_employee(
            organisation,
            'finalize-esi-employee@test.com',
            role='EMPLOYEE',
            employee_code='EMPF16L',
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )
        _create_ready_item(pay_run, employee)
        pay_run.status = PayrollRunStatus.CALCULATED
        pay_run.save(update_fields=['status'])

        finalize_pay_run(pay_run, actor=requester_user, skip_approval=True)

        payslip = Payslip.objects.get(pay_run=pay_run, employee=employee)
        assert str(payslip.esi_contribution_period_start) == '2026-04-01'
        assert str(payslip.esi_contribution_period_end) == '2026-09-30'
        assert payslip.esi_eligibility_mode == 'DIRECT'

    def test_rerun_payroll_run_requires_finalized_status(self):
        organisation = _create_active_organisation('Rerun Guard Org')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'rerun-guard@test.com',
            employee_code='EMPF16H',
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )

        with pytest.raises(ValueError):
            rerun_payroll_run(pay_run, actor=requester_user, requester_user=requester_user)

    def test_rerun_payroll_run_creates_linked_rerun(self):
        organisation = _create_active_organisation('Rerun Org')
        requester_user, requester_employee = _create_employee(
            organisation,
            'rerun@test.com',
            employee_code='EMPF16I',
        )
        _approver_user, approver_employee = _create_employee(
            organisation,
            'rerun-approver@test.com',
            employee_code='EMPF16J',
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
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
        pay_run.status = PayrollRunStatus.FINALIZED
        pay_run.approval_run = approval_run
        pay_run.save(update_fields=['status', 'approval_run'])

        rerun = rerun_payroll_run(
            pay_run,
            actor=requester_user,
            requester_user=requester_user,
            requester_employee=requester_employee,
        )

        assert rerun.source_run == pay_run
        assert rerun.status == PayrollRunStatus.DRAFT
        assert rerun.run_type == 'RERUN'
