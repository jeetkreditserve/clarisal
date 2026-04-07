from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.payroll.models import PayrollRunItemStatus
from apps.payroll.services import (
    assign_employee_compensation,
    calculate_pay_run,
    create_payroll_run,
    create_tax_slab_set,
    ensure_org_payroll_setup,
)
from apps.payroll.tests.test_service_run_calculation import (
    _basic_template,
    _create_active_organisation,
    _create_employee,
)
from apps.timeoff.models import LeaveWithoutPayEntry


@pytest.mark.django_db
def test_calculate_pay_run_uses_explicit_lwp_entries_and_approved_overtime():
    organisation = _create_active_organisation('Workforce Payroll Org')
    requester_user, _requester_employee = _create_employee(
        organisation,
        'workforce-requester@test.com',
        employee_code='EMPWP1',
    )
    _employee_user, employee = _create_employee(
        organisation,
        'workforce-employee@test.com',
        role='EMPLOYEE',
        employee_code='EMPWP2',
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
    LeaveWithoutPayEntry.objects.create(
        employee=employee,
        entry_date=date(2026, 4, 12),
        units=Decimal('2.00'),
        reason='Explicit LWP',
        source='MANUAL',
        status='APPROVED',
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
            'paid_fraction': Decimal('30.00'),
            'overtime_minutes': 60,
            'lop_days': Decimal('0.00'),
        }
        calculate_pay_run(pay_run, actor=requester_user)

    item = pay_run.items.get(employee=employee)
    assert item.status == PayrollRunItemStatus.READY
    assert item.snapshot['attendance_overtime_minutes'] == 60
    assert item.snapshot['attendance']['effective_lop_days'] == '2.00'
