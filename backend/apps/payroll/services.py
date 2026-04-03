from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal
import logging

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.approvals.models import ApprovalRequestKind, ApprovalRun, ApprovalRunStatus
from apps.approvals.services import cancel_approval_run, get_default_workflow
from apps.audit.services import log_audit_event
from apps.employees.models import Employee, EmployeeStatus, GovernmentIdType
from apps.notifications.models import NotificationKind
from apps.notifications.services import create_notification

from .models import (
    Arrears,
    CompensationAssignment,
    CompensationAssignmentLine,
    CompensationAssignmentStatus,
    CompensationTemplate,
    CompensationTemplateLine,
    CompensationTemplateStatus,
    FNFStatus,
    FullAndFinalSettlement,
    PayrollComponent,
    PayrollComponentType,
    PayrollRun,
    PayrollRunItem,
    PayrollRunItemStatus,
    PayrollRunStatus,
    PayrollRunType,
    PayrollTaxSlab,
    PayrollTaxSlabSet,
    Payslip,
    TaxRegime,
    InvestmentDeclaration,
    InvestmentSection,
    SECTION_LIMITS,
)

ZERO = Decimal('0.00')

# India statutory constants
INDIA_STANDARD_DEDUCTION = Decimal('75000.00')   # FY2024-25+ new regime
INDIA_CESS_RATE = Decimal('0.04')                 # 4% health & education cess
INDIA_REBATE_87A_MAX = Decimal('25000.00')
INDIA_REBATE_87A_THRESHOLD = Decimal('700000.00')
PF_RATE = Decimal('0.12')                         # 12% of basic
ESI_EMPLOYEE_RATE = Decimal('0.0075')             # 0.75% of gross
ESI_EMPLOYER_RATE = Decimal('0.0325')             # 3.25% of gross
ESI_WAGE_CEILING = Decimal('21000.00')            # ESI applies when gross ≤ ₹21,000

# Professional Tax — Maharashtra slab (most common; extend per state as needed)
_PT_MAHARASHTRA_SLABS = [
    (Decimal('10000.00'), Decimal('0.00')),    # < 10000: nil
    (Decimal('15000.00'), Decimal('150.00')), # 10000–14999: ₹150/month
    (None, Decimal('200.00')),                # ≥ 15000: ₹200/month
]


def _professional_tax_monthly(gross_monthly, state_code='MH'):
    """Return monthly Professional Tax for the given gross and state."""
    if state_code != 'MH':
        return ZERO
    for ceiling, amount in _PT_MAHARASHTRA_SLABS:
        if ceiling is None or gross_monthly < ceiling:
            return amount
    return ZERO


def _current_fiscal_year():
    today = date.today()
    if today.month >= 4:
        return f'{today.year}-{today.year + 1}'
    return f'{today.year - 1}-{today.year}'


DEFAULT_COMPONENTS = [
    {'code': 'BASIC', 'name': 'Basic Pay', 'component_type': PayrollComponentType.EARNING, 'is_taxable': True},
    {'code': 'HRA', 'name': 'House Rent Allowance', 'component_type': PayrollComponentType.EARNING, 'is_taxable': True},
    {'code': 'SPECIAL_ALLOWANCE', 'name': 'Special Allowance', 'component_type': PayrollComponentType.EARNING, 'is_taxable': True},
    {'code': 'PF_EMPLOYEE', 'name': 'Employee PF', 'component_type': PayrollComponentType.EMPLOYEE_DEDUCTION, 'is_taxable': False},
    {'code': 'PF_EMPLOYER', 'name': 'Employer PF', 'component_type': PayrollComponentType.EMPLOYER_CONTRIBUTION, 'is_taxable': False},
    {'code': 'ESI_EMPLOYEE', 'name': 'ESI (Employee)', 'component_type': PayrollComponentType.EMPLOYEE_DEDUCTION, 'is_taxable': False},
    {'code': 'ESI_EMPLOYER', 'name': 'ESI (Employer)', 'component_type': PayrollComponentType.EMPLOYER_CONTRIBUTION, 'is_taxable': False},
    {'code': 'PROFESSIONAL_TAX', 'name': 'Professional Tax', 'component_type': PayrollComponentType.EMPLOYEE_DEDUCTION, 'is_taxable': False},
]
DEFAULT_TAX_SLABS = [
    # India new regime FY2024-25 (7-slab structure)
    {'min_income': Decimal('0.00'), 'max_income': Decimal('300000.00'), 'rate_percent': Decimal('0.00')},
    {'min_income': Decimal('300000.00'), 'max_income': Decimal('700000.00'), 'rate_percent': Decimal('5.00')},
    {'min_income': Decimal('700000.00'), 'max_income': Decimal('1000000.00'), 'rate_percent': Decimal('10.00')},
    {'min_income': Decimal('1000000.00'), 'max_income': Decimal('1200000.00'), 'rate_percent': Decimal('15.00')},
    {'min_income': Decimal('1200000.00'), 'max_income': Decimal('1500000.00'), 'rate_percent': Decimal('20.00')},
    {'min_income': Decimal('1500000.00'), 'max_income': None, 'rate_percent': Decimal('30.00')},
]


def _normalize_decimal(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value.quantize(Decimal('0.01'))
    return Decimal(str(value)).quantize(Decimal('0.01'))


def _fiscal_year_for_period(period_year, period_month):
    if period_month >= 4:
        return f'{period_year}-{period_year + 1}'
    return f'{period_year - 1}-{period_year}'


def _get_or_create_component(organisation, payload):
    component, _ = PayrollComponent.objects.get_or_create(
        organisation=organisation,
        code=payload['component_code'],
        defaults={
            'name': payload['name'],
            'component_type': payload['component_type'],
            'is_taxable': payload.get('is_taxable', True),
            'is_system_default': False,
        },
    )
    changed = False
    for field, key in (
        ('name', 'name'),
        ('component_type', 'component_type'),
        ('is_taxable', 'is_taxable'),
    ):
        expected = payload.get(key, getattr(component, field))
        if getattr(component, field) != expected:
            setattr(component, field, expected)
            changed = True
    if changed:
        component.save()
    return component


def _fmt_inr(val):
    """Format a numeric string or Decimal as ₹XX,XX,XXX.XX (Indian notation)."""
    try:
        amount = Decimal(str(val)).quantize(Decimal('0.01'))
    except Exception:
        return str(val)
    negative = amount < 0
    amount = abs(amount)
    int_part, dec_part = f'{amount:.2f}'.split('.')
    # Indian grouping: last 3 digits, then groups of 2
    if len(int_part) > 3:
        last3 = int_part[-3:]
        rest = int_part[:-3]
        groups = []
        while rest:
            groups.append(rest[-2:])
            rest = rest[:-2]
        int_formatted = ','.join(reversed(groups)) + ',' + last3
    else:
        int_formatted = int_part
    sign = '-' if negative else ''
    return f'{sign}₹{int_formatted}.{dec_part}'


def _build_rendered_payslip(snapshot):
    """
    Generate a structured, readable payslip text from the finalized snapshot.
    Mimics the layout of Zoho Payroll / Keka payslips for easy reading.
    """
    SEP = '─' * 60
    THIN = '·' * 60

    def row(label, amount, indent=2):
        label_str = (' ' * indent) + label
        amount_str = _fmt_inr(amount)
        return f'{label_str:<44}{amount_str:>16}'

    period = snapshot.get('period_label', '')
    emp_name = snapshot.get('employee_name', '')
    paid_days = snapshot.get('paid_days', '')
    total_days = snapshot.get('total_days_in_period', '')

    out = [
        SEP,
        f'{"PAYSLIP":^60}',
        f'{"Period: " + period:^60}',
        SEP,
        f'  Employee : {emp_name}',
    ]
    if paid_days and total_days and str(paid_days) != str(total_days):
        out.append(f'  Paid Days: {paid_days} of {total_days} days')
    out.append(THIN)

    # Earnings section
    lines = snapshot.get('lines', [])
    earnings = [l for l in lines if l.get('component_type') == 'EARNING']
    if earnings:
        out.append('  EARNINGS')
        for e in earnings:
            out.append(row(e.get('component_name', ''), e.get('monthly_amount', '0')))
    arrears = snapshot.get('arrears', '0')
    try:
        if Decimal(str(arrears)) > ZERO:
            out.append(row('Arrears', arrears))
    except Exception:
        pass
    out.append(row('Gross Salary', snapshot.get('gross_pay', '0')))
    out.append(THIN)

    # Deductions section
    emp_deductions = [
        l for l in lines
        if l.get('component_type') == 'EMPLOYEE_DEDUCTION'
        and l.get('component_code') not in ('', None)
    ]
    out.append('  DEDUCTIONS')
    for d in emp_deductions:
        label = d.get('component_name', '')
        if d.get('auto_calculated'):
            label += ' *'
        out.append(row(label, d.get('monthly_amount', '0')))

    # LOP
    lop_days = snapshot.get('lop_days', '0')
    lop_deduction = snapshot.get('lop_deduction', '0')
    try:
        if Decimal(str(lop_deduction)) > ZERO:
            out.append(row(f'Loss of Pay ({lop_days} day(s))', lop_deduction))
    except Exception:
        pass

    # TDS line
    out.append(row('TDS (Income Tax)', snapshot.get('income_tax', '0')))
    out.append(row('Total Deductions', snapshot.get('total_deductions', '0')))
    out.append(THIN)

    # Employer contributions
    emp_contributions = [
        l for l in lines
        if l.get('component_type') == 'EMPLOYER_CONTRIBUTION'
        and l.get('component_code') not in ('', None)
    ]
    if emp_contributions:
        out.append('  EMPLOYER CONTRIBUTIONS  (not deducted from your pay)')
        for c in emp_contributions:
            label = c.get('component_name', '')
            if c.get('auto_calculated'):
                label += ' *'
            out.append(row(label, c.get('monthly_amount', '0')))
        out.append(THIN)

    # Tax computation detail
    ann_gross = snapshot.get('annual_taxable_gross')
    if ann_gross:
        out.append('  TAX COMPUTATION (Annual)')
        out.append(row('  Gross Taxable Income', ann_gross))
        out.append(row('  Less: Standard Deduction', snapshot.get('annual_standard_deduction', '0')))
        out.append(row('  Net Taxable Income', snapshot.get('annual_taxable_after_sd', '0')))
        out.append(row('  Income Tax (as per slabs)', snapshot.get('annual_tax_before_cess', '0')))
        out.append(row('  Health & Education Cess (4%)', snapshot.get('annual_cess', '0')))
        out.append(row('  Total Annual Tax (TDS)', snapshot.get('annual_tax_total', '0')))
        out.append(THIN)

    # Net pay — prominent
    out.append(SEP)
    net_str = _fmt_inr(snapshot.get('net_pay', '0'))
    out.append(f'  NET PAY (Take-Home){net_str:>40}')
    out.append(SEP)
    out.append('  * auto-calculated statutory component')

    return '\n'.join(out)


def _summarize_pay_run_exceptions(pay_run):
    exception_items = list(
        pay_run.items.filter(status=PayrollRunItemStatus.EXCEPTION).select_related('employee__user').order_by('employee__employee_code', 'created_at')
    )
    if not exception_items:
        return ''

    summary_parts = []
    for item in exception_items[:3]:
        employee_name = item.employee.user.full_name or item.employee.employee_code or str(item.employee_id)
        summary_parts.append(f'{employee_name}: {item.message or "Payroll data is incomplete."}')
    if len(exception_items) > 3:
        summary_parts.append(f'+{len(exception_items) - 3} more')
    return 'Resolve payroll exceptions before proceeding: ' + '; '.join(summary_parts)


def _notify_employees_payroll_finalized(pay_run, actor=None):
    from apps.notifications.tasks import send_payroll_ready_email

    period_label = date(pay_run.period_year, pay_run.period_month, 1).strftime('%B %Y')
    for payslip in pay_run.payslips.select_related('employee__user').all():
        recipient = payslip.employee.user
        create_notification(
            recipient=recipient,
            kind=NotificationKind.PAYROLL_FINALIZED,
            title=f'Your payslip for {period_label} is ready',
            body='Your payslip has been finalized. View it in your payslips section.',
            organisation=pay_run.organisation,
            related_object=pay_run,
            actor=actor,
        )
        transaction.on_commit(
            lambda user_id=str(recipient.id), label=period_label: send_payroll_ready_email.delay(
                user_id,
                pay_period=label,
            )
        )


def _calculate_annual_tax(tax_slab_set, annual_taxable_income):
    taxable = _normalize_decimal(annual_taxable_income) or ZERO
    annual_tax = ZERO
    for slab in tax_slab_set.slabs.order_by('min_income', 'created_at'):
        slab_start = slab.min_income
        slab_end = slab.max_income
        if taxable <= slab_start:
            continue
        upper_bound = taxable if slab_end is None else min(taxable, slab_end)
        taxable_slice = upper_bound - slab_start
        if taxable_slice <= ZERO:
            continue
        annual_tax += taxable_slice * (slab.rate_percent / Decimal('100.00'))
        if slab_end is None or taxable <= slab_end:
            break
    return annual_tax.quantize(Decimal('0.01'))


def calculate_taxable_income_after_standard_deduction(gross_taxable_income):
    taxable_income = (_normalize_decimal(gross_taxable_income) or ZERO) - INDIA_STANDARD_DEDUCTION
    return max(ZERO, taxable_income).quantize(Decimal('0.01'))


def apply_cess(tax_before_cess):
    base_tax = _normalize_decimal(tax_before_cess) or ZERO
    return (base_tax * (Decimal('1.00') + INDIA_CESS_RATE)).quantize(Decimal('0.01'))


def calculate_income_tax_with_rebate(*, taxable_income, tax_slab_set):
    annual_taxable_income = _normalize_decimal(taxable_income) or ZERO
    tax_before_rebate = _calculate_annual_tax(tax_slab_set, annual_taxable_income)
    rebate_87a = ZERO
    if annual_taxable_income <= INDIA_REBATE_87A_THRESHOLD:
        rebate_87a = min(tax_before_rebate, INDIA_REBATE_87A_MAX).quantize(Decimal('0.01'))
    tax_after_rebate = max(ZERO, tax_before_rebate - rebate_87a).quantize(Decimal('0.01'))
    cess = (tax_after_rebate * INDIA_CESS_RATE).quantize(Decimal('0.01'))
    annual_tax = apply_cess(tax_after_rebate)
    return {
        'tax_before_rebate': tax_before_rebate,
        'rebate_87a': rebate_87a,
        'tax_after_rebate': tax_after_rebate,
        'cess': cess,
        'annual_tax': annual_tax,
    }


def ensure_non_negative_net_pay(net_pay):
    normalized_net_pay = _normalize_decimal(net_pay) or ZERO
    if normalized_net_pay < ZERO:
        logging.getLogger(__name__).warning(
            'Net pay calculated as negative (%s). Clamping to zero. Check deduction components.',
            normalized_net_pay,
        )
    return max(ZERO, normalized_net_pay).quantize(Decimal('0.01'))


def get_total_80c_deduction(employee, fiscal_year):
    total = (
        InvestmentDeclaration.objects.filter(
            employee=employee,
            fiscal_year=fiscal_year,
            section=InvestmentSection.SECTION_80C,
        ).aggregate(total=Sum('declared_amount'))['total']
        or ZERO
    )
    cap = SECTION_LIMITS[InvestmentSection.SECTION_80C]
    return min(_normalize_decimal(total) or ZERO, cap).quantize(Decimal('0.01'))


def calculate_taxable_income_with_investments(*, employee, annual_gross, fiscal_year, tax_regime):
    after_standard_deduction = calculate_taxable_income_after_standard_deduction(annual_gross)
    if tax_regime != TaxRegime.OLD:
        return after_standard_deduction

    total_deductions = ZERO
    for section, cap in SECTION_LIMITS.items():
        section_total = (
            InvestmentDeclaration.objects.filter(
                employee=employee,
                fiscal_year=fiscal_year,
                section=section,
            ).aggregate(total=Sum('declared_amount'))['total']
            or ZERO
        )
        total_deductions += min(_normalize_decimal(section_total) or ZERO, cap)
    return max(ZERO, after_standard_deduction - total_deductions).quantize(Decimal('0.01'))


def calculate_fnf_salary_proration(
    gross_monthly_salary: Decimal,
    last_working_day: date,
    period_year: int,
    period_month: int,
) -> Decimal:
    total_days = Decimal(str(monthrange(period_year, period_month)[1]))
    paid_days = Decimal(str(last_working_day.day))
    salary = _normalize_decimal(gross_monthly_salary) or ZERO
    return (salary * paid_days / total_days).quantize(Decimal('0.01'))


def calculate_leave_encashment_amount(
    leave_days: Decimal,
    monthly_basic_salary: Decimal,
) -> Decimal:
    per_day_basic = ((_normalize_decimal(monthly_basic_salary) or ZERO) / Decimal('26')).quantize(Decimal('0.01'))
    encashment_days = _normalize_decimal(leave_days) or ZERO
    return (encashment_days * per_day_basic).quantize(Decimal('0.01'))


def _get_assignment_monthly_amounts(assignment):
    gross_monthly_salary = ZERO
    monthly_basic_salary = ZERO
    for line in assignment.lines.select_related('component').order_by('sequence', 'created_at'):
        amount = _normalize_decimal(line.monthly_amount) or ZERO
        if line.component_type == PayrollComponentType.EARNING:
            gross_monthly_salary += amount
        if line.component_id and line.component.code == 'BASIC':
            monthly_basic_salary = amount
    return gross_monthly_salary, monthly_basic_salary


def _calculate_fnf_totals(employee, last_working_day):
    assignment = get_effective_compensation_assignment(employee, last_working_day)
    if assignment is None:
        return {
            'prorated_salary': ZERO,
            'leave_encashment': ZERO,
            'gross_payable': ZERO,
            'net_payable': ZERO,
        }

    gross_monthly_salary, monthly_basic_salary = _get_assignment_monthly_amounts(assignment)
    prorated_salary = calculate_fnf_salary_proration(
        gross_monthly_salary=gross_monthly_salary,
        last_working_day=last_working_day,
        period_year=last_working_day.year,
        period_month=last_working_day.month,
    )
    leave_encashment = ZERO
    if monthly_basic_salary > ZERO:
        leave_encashment = calculate_leave_encashment_amount(
            leave_days=ZERO,
            monthly_basic_salary=monthly_basic_salary,
        )
    gross_payable = (prorated_salary + leave_encashment).quantize(Decimal('0.01'))
    net_payable = gross_payable
    return {
        'prorated_salary': prorated_salary,
        'leave_encashment': leave_encashment,
        'gross_payable': gross_payable,
        'net_payable': net_payable,
    }


def create_full_and_final_settlement(employee, last_working_day: date, initiated_by=None, offboarding_process=None):
    totals = _calculate_fnf_totals(employee, last_working_day)
    fnf, created = FullAndFinalSettlement.objects.get_or_create(
        employee=employee,
        defaults={
            'offboarding_process': offboarding_process,
            'last_working_day': last_working_day,
            'status': FNFStatus.DRAFT,
            'prorated_salary': totals['prorated_salary'],
            'leave_encashment': totals['leave_encashment'],
            'gross_payable': totals['gross_payable'],
            'net_payable': totals['net_payable'],
            'created_by': initiated_by,
            'modified_by': initiated_by,
        },
    )
    update_fields = []
    if fnf.last_working_day != last_working_day:
        fnf.last_working_day = last_working_day
        update_fields.append('last_working_day')
    if offboarding_process is not None and fnf.offboarding_process_id != offboarding_process.id:
        fnf.offboarding_process = offboarding_process
        update_fields.append('offboarding_process')
    if fnf.status == FNFStatus.DRAFT:
        for field_name in ('prorated_salary', 'leave_encashment', 'gross_payable', 'net_payable'):
            if getattr(fnf, field_name) != totals[field_name]:
                setattr(fnf, field_name, totals[field_name])
                update_fields.append(field_name)
    if update_fields:
        fnf.modified_by = initiated_by
        update_fields.extend(['modified_by', 'modified_at'])
        fnf.save(update_fields=update_fields)
    log_audit_event(
        initiated_by,
        'payroll.fnf.created' if created else 'payroll.fnf.updated',
        organisation=employee.organisation,
        target=employee,
        payload={
            'fnf_settlement_id': str(fnf.id),
            'last_working_day': last_working_day.isoformat(),
            'status': fnf.status,
        },
    )
    return fnf


def get_employee_arrears_for_run(employee, pay_run) -> Decimal:
    total = (
        Arrears.objects.filter(
            employee=employee,
            pay_run=pay_run,
            is_included_in_payslip=False,
        ).aggregate(total=Sum('amount'))['total']
        or ZERO
    )
    return (_normalize_decimal(total) or ZERO).quantize(Decimal('0.01'))


def _get_active_tax_slab_set(organisation, fiscal_year, *, tax_regime=TaxRegime.NEW):
    is_old_regime = tax_regime == TaxRegime.OLD
    tax_slab_set = PayrollTaxSlabSet.objects.filter(
        organisation=organisation,
        fiscal_year=fiscal_year,
        is_active=True,
        is_old_regime=is_old_regime,
    ).order_by('-created_at').first()
    if tax_slab_set:
        return tax_slab_set
    tax_slab_set = PayrollTaxSlabSet.objects.filter(
        organisation=organisation,
        is_active=True,
        is_old_regime=is_old_regime,
    ).order_by('-created_at').first()
    if tax_slab_set:
        return tax_slab_set
    tax_slab_set = PayrollTaxSlabSet.objects.filter(
        organisation__isnull=True,
        is_system_master=True,
        country_code='IN',
        fiscal_year=fiscal_year,
        is_active=True,
        is_old_regime=is_old_regime,
    ).order_by('-created_at').first()
    if tax_slab_set:
        return tax_slab_set
    return PayrollTaxSlabSet.objects.filter(
        organisation__isnull=True,
        is_system_master=True,
        country_code='IN',
        is_active=True,
        is_old_regime=is_old_regime,
    ).order_by('-created_at').first()


def _ensure_global_default_tax_master(actor=None):
    tax_slab_set = PayrollTaxSlabSet.objects.filter(
        organisation__isnull=True,
        is_system_master=True,
        is_active=True,
        country_code='IN',
        is_old_regime=False,
    ).order_by('-created_at').first()
    if tax_slab_set:
        return tax_slab_set
    return create_tax_slab_set(
        fiscal_year=_current_fiscal_year(),
        name='Default India Payroll Master',
        country_code='IN',
        slabs=DEFAULT_TAX_SLABS,
        actor=actor,
        organisation=None,
        is_active=True,
        is_old_regime=False,
    )


def _resolve_payroll_requester_context(requester_user=None, requester_employee=None, organisation=None):
    if requester_employee is not None:
        return requester_employee.organisation, requester_user or requester_employee.user, requester_employee
    if requester_user is None or organisation is None:
        raise ValueError('A payroll requester user and organisation are required.')
    return organisation, requester_user, None


def _create_payroll_approval_run(subject, request_kind, organisation, requester_user, requester_employee=None, subject_label=''):
    workflow = get_default_workflow(organisation, request_kind)
    if workflow is None:
        raise ValueError(f'No active default approval workflow is configured for {request_kind.lower().replace("_", " ")} requests.')
    first_stage = workflow.stages.prefetch_related('approvers__approver_employee__user').order_by('sequence').first()
    if first_stage is None:
        raise ValueError('The selected approval workflow does not contain any stages.')

    with transaction.atomic():
        approval_run = ApprovalRun.objects.create(
            organisation=organisation,
            workflow=workflow,
            request_kind=request_kind,
            requested_by=requester_employee,
            requested_by_user=requester_user,
            status=ApprovalRunStatus.PENDING,
            current_stage_sequence=first_stage.sequence,
            subject_label=subject_label or str(subject),
            content_type=ContentType.objects.get_for_model(subject.__class__),
            object_id=subject.id,
        )
        from apps.approvals.services import _create_stage_actions

        _create_stage_actions(approval_run, first_stage)

    log_audit_event(
        requester_user,
        'approval.run.created',
        organisation=organisation,
        target=approval_run,
        payload={'request_kind': request_kind, 'workflow_id': str(workflow.id)},
    )
    return approval_run


def ensure_org_payroll_setup(organisation, actor=None):
    master = _ensure_global_default_tax_master(actor=actor)
    org_tax_slab_set = PayrollTaxSlabSet.objects.filter(
        organisation=organisation,
        is_active=True,
        is_old_regime=False,
    ).order_by('-created_at').first()
    if org_tax_slab_set is None:
        org_tax_slab_set = create_tax_slab_set(
            fiscal_year=master.fiscal_year,
            name=f'{master.name} • {organisation.name}',
            country_code=master.country_code,
            slabs=[
                {
                    'min_income': slab.min_income,
                    'max_income': slab.max_income,
                    'rate_percent': slab.rate_percent,
                }
                for slab in master.slabs.all()
            ],
            actor=actor,
            organisation=organisation,
            source_set=master,
            is_active=True,
            is_old_regime=False,
        )

    components = []
    for payload in DEFAULT_COMPONENTS:
        component, _ = PayrollComponent.objects.get_or_create(
            organisation=organisation,
            code=payload['code'],
            defaults={
                'name': payload['name'],
                'component_type': payload['component_type'],
                'is_taxable': payload['is_taxable'],
                'is_system_default': True,
            },
        )
        components.append(component)
    return {'tax_slab_set': org_tax_slab_set, 'components': components}


def create_tax_slab_set(*, fiscal_year, name, country_code, slabs, actor=None, organisation=None, source_set=None, is_active=True, is_old_regime=False):
    if not slabs:
        raise ValueError('At least one tax slab is required.')
    is_system_master = organisation is None
    with transaction.atomic():
        tax_slab_set = PayrollTaxSlabSet.objects.create(
            organisation=organisation,
            source_set=source_set,
            name=name,
            country_code=country_code,
            fiscal_year=fiscal_year,
            is_active=is_active,
            is_system_master=is_system_master,
            is_old_regime=is_old_regime,
        )
        for slab in slabs:
            PayrollTaxSlab.objects.create(
                slab_set=tax_slab_set,
                min_income=_normalize_decimal(slab['min_income']),
                max_income=_normalize_decimal(slab.get('max_income')),
                rate_percent=_normalize_decimal(slab['rate_percent']),
            )
    log_audit_event(actor, 'payroll.tax_slab_set.created', organisation=organisation, target=tax_slab_set)
    return tax_slab_set


def update_tax_slab_set(tax_slab_set, *, name=None, fiscal_year=None, is_active=None, is_old_regime=None, slabs=None, actor=None):
    if name is not None:
        tax_slab_set.name = name
    if fiscal_year is not None:
        tax_slab_set.fiscal_year = fiscal_year
    if is_active is not None:
        tax_slab_set.is_active = is_active
    if is_old_regime is not None:
        tax_slab_set.is_old_regime = is_old_regime
    tax_slab_set.save()
    if slabs is not None:
        tax_slab_set.slabs.all().delete()
        for slab in slabs:
            PayrollTaxSlab.objects.create(
                slab_set=tax_slab_set,
                min_income=_normalize_decimal(slab['min_income']),
                max_income=_normalize_decimal(slab.get('max_income')),
                rate_percent=_normalize_decimal(slab['rate_percent']),
            )
    log_audit_event(actor, 'payroll.tax_slab_set.updated', organisation=tax_slab_set.organisation, target=tax_slab_set)
    return tax_slab_set


def create_compensation_template(organisation, *, name, description='', lines, actor=None):
    ensure_org_payroll_setup(organisation, actor=actor)
    if not lines:
        raise ValueError('At least one compensation line is required.')
    with transaction.atomic():
        template = CompensationTemplate.objects.create(
            organisation=organisation,
            name=name,
            description=description,
            status=CompensationTemplateStatus.DRAFT,
        )
        for index, line in enumerate(lines, start=1):
            component = _get_or_create_component(organisation, line)
            CompensationTemplateLine.objects.create(
                template=template,
                component=component,
                monthly_amount=_normalize_decimal(line['monthly_amount']),
                sequence=index,
            )
    log_audit_event(actor, 'payroll.compensation_template.created', organisation=organisation, target=template)
    return template


def update_compensation_template(template, *, name=None, description=None, lines=None, actor=None):
    if name is not None:
        template.name = name
    if description is not None:
        template.description = description
    if template.status == CompensationTemplateStatus.APPROVED:
        template.status = CompensationTemplateStatus.DRAFT
    template.save()
    if lines is not None:
        template.lines.all().delete()
        for index, line in enumerate(lines, start=1):
            component = _get_or_create_component(template.organisation, line)
            CompensationTemplateLine.objects.create(
                template=template,
                component=component,
                monthly_amount=_normalize_decimal(line['monthly_amount']),
                sequence=index,
            )
    log_audit_event(actor, 'payroll.compensation_template.updated', organisation=template.organisation, target=template)
    return template


def submit_compensation_template_for_approval(template, *, requester_user, requester_employee=None):
    if template.status not in [CompensationTemplateStatus.DRAFT, CompensationTemplateStatus.REJECTED]:
        raise ValueError('Only draft or rejected templates can be submitted for approval.')
    organisation, requester_user, requester_employee = _resolve_payroll_requester_context(
        requester_user=requester_user,
        requester_employee=requester_employee,
        organisation=template.organisation,
    )
    approval_run = _create_payroll_approval_run(
        template,
        ApprovalRequestKind.COMPENSATION_TEMPLATE_CHANGE,
        organisation,
        requester_user,
        requester_employee=requester_employee,
        subject_label=template.name,
    )
    template.approval_run = approval_run
    template.status = CompensationTemplateStatus.PENDING_APPROVAL
    template.save(update_fields=['approval_run', 'status', 'modified_at'])
    return template


def assign_employee_compensation(employee, template, *, effective_from, actor=None, auto_approve=False, tax_regime=TaxRegime.NEW):
    version = employee.compensation_assignments.count() + 1
    with transaction.atomic():
        assignment = CompensationAssignment.objects.create(
            employee=employee,
            template=template,
            effective_from=effective_from,
            version=version,
            tax_regime=tax_regime,
            status=CompensationAssignmentStatus.APPROVED if auto_approve else CompensationAssignmentStatus.DRAFT,
        )
        for line in template.lines.select_related('component').all():
            CompensationAssignmentLine.objects.create(
                assignment=assignment,
                component=line.component,
                component_name=line.component.name,
                component_type=line.component.component_type,
                monthly_amount=line.monthly_amount,
                is_taxable=line.component.is_taxable,
                sequence=line.sequence,
            )
    log_audit_event(actor, 'payroll.compensation_assignment.created', organisation=employee.organisation, target=assignment)
    return assignment


def submit_compensation_assignment_for_approval(assignment, *, requester_user, requester_employee=None):
    if assignment.status not in [CompensationAssignmentStatus.DRAFT, CompensationAssignmentStatus.REJECTED]:
        raise ValueError('Only draft or rejected compensation assignments can be submitted for approval.')
    organisation, requester_user, requester_employee = _resolve_payroll_requester_context(
        requester_user=requester_user,
        requester_employee=requester_employee,
        organisation=assignment.employee.organisation,
    )
    approval_run = _create_payroll_approval_run(
        assignment,
        ApprovalRequestKind.SALARY_REVISION,
        organisation,
        requester_user,
        requester_employee=requester_employee,
        subject_label=f'{assignment.employee.user.full_name} salary revision',
    )
    assignment.approval_run = approval_run
    assignment.status = CompensationAssignmentStatus.PENDING_APPROVAL
    assignment.save(update_fields=['approval_run', 'status', 'modified_at'])
    return assignment


def get_effective_compensation_assignment(employee, as_of_date):
    return employee.compensation_assignments.filter(
        effective_from__lte=as_of_date,
        status=CompensationAssignmentStatus.APPROVED,
    ).order_by('-effective_from', '-version', '-created_at').first()


def create_payroll_run(organisation, *, period_year, period_month, actor=None, requester_user=None, requester_employee=None, source_run=None, run_type=PayrollRunType.REGULAR, name='', use_attendance_inputs=False):
    ensure_org_payroll_setup(organisation, actor=actor or requester_user)
    if not name:
        month_label = date(period_year, period_month, 1).strftime('%b %Y')
        name = f'{month_label} Payroll'
        if run_type == PayrollRunType.RERUN:
            name = f'{month_label} Payroll Rerun'
    pay_run = PayrollRun.objects.create(
        organisation=organisation,
        name=name,
        period_year=period_year,
        period_month=period_month,
        run_type=run_type,
        use_attendance_inputs=use_attendance_inputs,
        source_run=source_run,
    )
    log_audit_event(actor or requester_user, 'payroll.run.created', organisation=organisation, target=pay_run)
    return pay_run


def _employee_payroll_snapshot(employee):
    return {
        'has_primary_bank': employee.bank_accounts.filter(is_primary=True).exists(),
        'has_pan': employee.government_ids.filter(id_type=GovernmentIdType.PAN).exists(),
        'has_aadhaar': employee.government_ids.filter(id_type=GovernmentIdType.AADHAAR).exists(),
    }


def calculate_pay_run(pay_run, *, actor=None):
    if pay_run.status == PayrollRunStatus.APPROVED:
        raise ValueError('Approved payroll runs cannot be recalculated. Create a rerun or move the run back to draft first.')
    if pay_run.status == PayrollRunStatus.FINALIZED:
        raise ValueError('Finalized payroll runs cannot be recalculated.')
    if pay_run.approval_run_id and pay_run.approval_run.status == ApprovalRunStatus.PENDING:
        cancel_approval_run(pay_run.approval_run, actor=actor)
        pay_run.approval_run = None

    period_start = date(pay_run.period_year, pay_run.period_month, 1)
    period_end = date(pay_run.period_year, pay_run.period_month, monthrange(pay_run.period_year, pay_run.period_month)[1])
    total_days_in_period = period_end.day
    fiscal_year = _fiscal_year_for_period(pay_run.period_year, pay_run.period_month)
    # Determine org state code for Professional Tax (default Maharashtra)
    from apps.timeoff.models import LeaveRequest, LeaveRequestStatus
    org_state_code = getattr(pay_run.organisation, 'state_code', 'MH') or 'MH'

    with transaction.atomic():
        pay_run.items.all().delete()
        run_attendance_snapshot = {
            'attendance_source': 'attendance_service' if pay_run.use_attendance_inputs else 'not_applied',
            'period_start': str(period_start),
            'period_end': str(period_end),
            'use_attendance_inputs': pay_run.use_attendance_inputs,
            'employee_count': 0,
            'ready_item_count': 0,
            'exception_item_count': 0,
            'total_attendance_paid_days': '0.00',
            'total_lop_days': '0.00',
            'total_overtime_minutes': 0,
            'employees': [],
        }
        total_attendance_paid_days = ZERO
        total_lop_days = ZERO
        total_overtime_minutes = 0
        employees = Employee.objects.filter(
            organisation=pay_run.organisation,
            status=EmployeeStatus.ACTIVE,
        ).select_related('user', 'office_location')
        assignments_by_employee = {}
        assignments = (
            CompensationAssignment.objects.filter(
                employee__organisation=pay_run.organisation,
                status=CompensationAssignmentStatus.APPROVED,
                effective_from__lte=period_end,
            )
            .select_related('employee', 'template')
            .prefetch_related('lines__component')
            .order_by('employee_id', '-effective_from', '-version', '-created_at')
        )
        for assignment in assignments:
            assignments_by_employee.setdefault(assignment.employee_id, assignment)
        for employee in employees:
            run_attendance_snapshot['employee_count'] += 1
            assignment = assignments_by_employee.get(employee.id)
            if assignment is None:
                PayrollRunItem.objects.create(
                    pay_run=pay_run,
                    employee=employee,
                    status=PayrollRunItemStatus.EXCEPTION,
                    message='No approved compensation assignment is effective for this period.',
                    snapshot={'readiness': _employee_payroll_snapshot(employee)},
                )
                run_attendance_snapshot['exception_item_count'] += 1
                run_attendance_snapshot['employees'].append(
                    {
                        'employee_id': str(employee.id),
                        'employee_code': employee.employee_code or '',
                        'status': 'EXCEPTION',
                        'reason': 'No approved compensation assignment is effective for this period.',
                    }
                )
                continue
            tax_slab_set = _get_active_tax_slab_set(
                pay_run.organisation,
                fiscal_year,
                tax_regime=assignment.tax_regime,
            )
            if tax_slab_set is None:
                PayrollRunItem.objects.create(
                    pay_run=pay_run,
                    employee=employee,
                    status=PayrollRunItemStatus.EXCEPTION,
                    message=f'No active {assignment.tax_regime.lower()} tax slab set is configured for this payroll period.',
                    snapshot={
                        'readiness': _employee_payroll_snapshot(employee),
                        'tax_regime': assignment.tax_regime,
                    },
                )
                run_attendance_snapshot['exception_item_count'] += 1
                run_attendance_snapshot['employees'].append(
                    {
                        'employee_id': str(employee.id),
                        'employee_code': employee.employee_code or '',
                        'status': 'EXCEPTION',
                        'reason': f'No active {assignment.tax_regime.lower()} tax slab set is configured for this payroll period.',
                    }
                )
                continue

            # ── Step 1: collect raw component amounts ────────────────────────
            raw_gross = ZERO
            raw_employee_deductions = ZERO
            raw_employer_contributions = ZERO
            taxable_monthly = ZERO
            basic_pay = ZERO
            has_pf_employee_line = False
            has_pf_employer_line = False
            lines_snapshot = []

            for line in assignment.lines.all().order_by('sequence', 'created_at'):
                amount = _normalize_decimal(line.monthly_amount)
                comp_code = line.component.code if line.component_id else ''

                if comp_code == 'BASIC' and line.component_type == PayrollComponentType.EARNING:
                    basic_pay = amount
                if comp_code == 'PF_EMPLOYEE':
                    has_pf_employee_line = True
                    # Skip the template amount — we'll replace with formula below
                    lines_snapshot.append({
                        'component_code': comp_code,
                        'component_name': line.component_name,
                        'component_type': line.component_type,
                        'monthly_amount': str(amount),  # template value (for reference)
                        'is_taxable': line.is_taxable,
                        'auto_calculated': False,
                        'template_amount': str(amount),
                    })
                    continue
                if comp_code == 'PF_EMPLOYER':
                    has_pf_employer_line = True
                    lines_snapshot.append({
                        'component_code': comp_code,
                        'component_name': line.component_name,
                        'component_type': line.component_type,
                        'monthly_amount': str(amount),
                        'is_taxable': line.is_taxable,
                        'auto_calculated': False,
                        'template_amount': str(amount),
                    })
                    continue

                lines_snapshot.append({
                    'component_code': comp_code,
                    'component_name': line.component_name,
                    'component_type': line.component_type,
                    'monthly_amount': str(amount),
                    'is_taxable': line.is_taxable,
                    'auto_calculated': False,
                })

                if line.component_type in [PayrollComponentType.EARNING, PayrollComponentType.REIMBURSEMENT]:
                    raw_gross += amount
                    if line.is_taxable:
                        taxable_monthly += amount
                elif line.component_type == PayrollComponentType.EMPLOYEE_DEDUCTION:
                    raw_employee_deductions += amount
                elif line.component_type == PayrollComponentType.EMPLOYER_CONTRIBUTION:
                    raw_employer_contributions += amount

            gross_pay = raw_gross
            arrears_amount = get_employee_arrears_for_run(employee, pay_run)
            if arrears_amount > ZERO:
                gross_pay = (gross_pay + arrears_amount).quantize(Decimal('0.01'))
                taxable_monthly = (taxable_monthly + arrears_amount).quantize(Decimal('0.01'))

            # ── Step 2: PF auto-calculation (12% of basic) ──────────────────
            auto_pf = ZERO
            if basic_pay > ZERO:
                auto_pf = (basic_pay * PF_RATE).quantize(Decimal('0.01'))
                raw_employee_deductions += auto_pf
                raw_employer_contributions += auto_pf
                # Update PF lines in snapshot with auto-calculated amounts
                for snap_line in lines_snapshot:
                    if snap_line.get('component_code') == 'PF_EMPLOYEE':
                        snap_line['monthly_amount'] = str(auto_pf)
                        snap_line['auto_calculated'] = True
                    elif snap_line.get('component_code') == 'PF_EMPLOYER':
                        snap_line['monthly_amount'] = str(auto_pf)
                        snap_line['auto_calculated'] = True
                if not has_pf_employee_line:
                    lines_snapshot.append({
                        'component_code': 'PF_EMPLOYEE',
                        'component_name': 'Employee PF (12% of Basic)',
                        'component_type': PayrollComponentType.EMPLOYEE_DEDUCTION,
                        'monthly_amount': str(auto_pf),
                        'is_taxable': False,
                        'auto_calculated': True,
                    })
                if not has_pf_employer_line:
                    lines_snapshot.append({
                        'component_code': 'PF_EMPLOYER',
                        'component_name': 'Employer PF (12% of Basic)',
                        'component_type': PayrollComponentType.EMPLOYER_CONTRIBUTION,
                        'monthly_amount': str(auto_pf),
                        'is_taxable': False,
                        'auto_calculated': True,
                    })

            # ── Step 3: ESI auto-calculation ─────────────────────────────────
            esi_employee = ZERO
            esi_employer = ZERO
            if gross_pay <= ESI_WAGE_CEILING:
                esi_employee = (gross_pay * ESI_EMPLOYEE_RATE).quantize(Decimal('0.01'))
                esi_employer = (gross_pay * ESI_EMPLOYER_RATE).quantize(Decimal('0.01'))
                raw_employee_deductions += esi_employee
                raw_employer_contributions += esi_employer
                lines_snapshot.append({
                    'component_code': 'ESI_EMPLOYEE',
                    'component_name': 'ESI - Employee (0.75%)',
                    'component_type': PayrollComponentType.EMPLOYEE_DEDUCTION,
                    'monthly_amount': str(esi_employee),
                    'is_taxable': False,
                    'auto_calculated': True,
                })
                lines_snapshot.append({
                    'component_code': 'ESI_EMPLOYER',
                    'component_name': 'ESI - Employer (3.25%)',
                    'component_type': PayrollComponentType.EMPLOYER_CONTRIBUTION,
                    'monthly_amount': str(esi_employer),
                    'is_taxable': False,
                    'auto_calculated': True,
                })

            # ── Step 4: Professional Tax ─────────────────────────────────────
            employee_state = 'MH'
            if employee.office_location_id and hasattr(employee.office_location, 'state_code'):
                employee_state = employee.office_location.state_code or org_state_code
            pt_monthly = _professional_tax_monthly(gross_pay, employee_state)
            if pt_monthly > ZERO:
                raw_employee_deductions += pt_monthly
                lines_snapshot.append({
                    'component_code': 'PROFESSIONAL_TAX',
                    'component_name': 'Professional Tax',
                    'component_type': PayrollComponentType.EMPLOYEE_DEDUCTION,
                    'monthly_amount': str(pt_monthly),
                    'is_taxable': False,
                    'auto_calculated': True,
                })

            employee_deductions = raw_employee_deductions
            employer_contributions = raw_employer_contributions

            # ── Step 5: Pro-ration for joining or exit month ─────────────────
            joining = employee.date_of_joining
            exit_date = employee.date_of_exit
            paid_days = total_days_in_period

            if joining and period_start <= joining <= period_end:
                # New joiner — pay from joining date to end of month
                paid_days = (period_end - joining).days + 1
            elif exit_date and period_start <= exit_date < period_end:
                # Exiting employee — pay from start of month to exit date
                paid_days = (exit_date - period_start).days + 1

            if paid_days < total_days_in_period:
                prorate_factor = Decimal(paid_days) / Decimal(total_days_in_period)
                gross_pay = (gross_pay * prorate_factor).quantize(Decimal('0.01'))
                taxable_monthly = (taxable_monthly * prorate_factor).quantize(Decimal('0.01'))
                employee_deductions = (employee_deductions * prorate_factor).quantize(Decimal('0.01'))
                employer_contributions = (employer_contributions * prorate_factor).quantize(Decimal('0.01'))
                auto_pf = (auto_pf * prorate_factor).quantize(Decimal('0.01'))
                esi_employee = (esi_employee * prorate_factor).quantize(Decimal('0.01'))
                esi_employer = (esi_employer * prorate_factor).quantize(Decimal('0.01'))
                pt_monthly = (pt_monthly * prorate_factor).quantize(Decimal('0.01'))
            else:
                prorate_factor = Decimal('1.00')

            # ── Step 6: Attendance-backed payable days and LOP ───────────────
            active_period_start = max(period_start, joining) if joining and joining > period_start else period_start
            active_period_end = min(period_end, exit_date) if exit_date and exit_date < period_end else period_end
            attendance_paid_days = Decimal(str(paid_days))
            attendance_overtime_minutes = 0
            if pay_run.use_attendance_inputs and active_period_start <= active_period_end:
                try:
                    from apps.attendance.services import get_payroll_attendance_summary

                    attendance_summary = get_payroll_attendance_summary(
                        employee,
                        period_start=active_period_start,
                        period_end=active_period_end,
                    )
                    attendance_paid_days = attendance_summary['paid_fraction']
                    attendance_overtime_minutes = attendance_summary['overtime_minutes']
                except Exception:  # noqa: BLE001
                    attendance_summary = None
            else:
                attendance_summary = None

            lop_result = LeaveRequest.objects.filter(
                employee=employee,
                leave_type__is_loss_of_pay=True,
                status=LeaveRequestStatus.APPROVED,
                start_date__gte=period_start,
                start_date__lte=period_end,
            ).aggregate(total=Sum('total_units'))
            leave_only_lop_days = _normalize_decimal(lop_result['total']) or ZERO
            expected_paid_days = Decimal(str(paid_days))
            attendance_based_lop = max(ZERO, expected_paid_days - attendance_paid_days) if pay_run.use_attendance_inputs else ZERO
            lop_days = max(leave_only_lop_days, attendance_based_lop)
            lop_deduction = ZERO
            if lop_days > ZERO and gross_pay > ZERO and total_days_in_period > 0:
                daily_gross = (gross_pay / Decimal(total_days_in_period)).quantize(Decimal('0.01'))
                lop_deduction = (daily_gross * lop_days).quantize(Decimal('0.01'))
                lop_deduction = min(lop_deduction, gross_pay)

            attendance_context = {
                'period_start': str(period_start),
                'period_end': str(period_end),
                'active_period_start': str(active_period_start),
                'active_period_end': str(active_period_end),
                'expected_paid_days': str(expected_paid_days),
                'attendance_paid_days': str(attendance_paid_days),
                'leave_only_lop_days': str(leave_only_lop_days),
                'attendance_based_lop_days': str(attendance_based_lop),
                'effective_lop_days': str(lop_days),
                'attendance_overtime_minutes': attendance_overtime_minutes,
                'attendance_source': 'attendance_service' if attendance_summary is not None else ('not_applied' if not pay_run.use_attendance_inputs else 'unavailable'),
                'use_attendance_inputs': pay_run.use_attendance_inputs,
            }

            total_attendance_paid_days += attendance_paid_days
            total_lop_days += lop_days
            total_overtime_minutes += attendance_overtime_minutes
            run_attendance_snapshot['ready_item_count'] += 1
            run_attendance_snapshot['employees'].append(
                {
                    'employee_id': str(employee.id),
                    'employee_code': employee.employee_code or '',
                    'status': 'READY',
                    'active_period_start': str(active_period_start),
                    'active_period_end': str(active_period_end),
                    'attendance_paid_days': str(attendance_paid_days),
                    'effective_lop_days': str(lop_days),
                    'attendance_overtime_minutes': attendance_overtime_minutes,
                }
            )

            # ── Step 7: Income tax with standard deduction + cess ────────────
            annual_taxable_gross = (taxable_monthly * Decimal('12.00')).quantize(Decimal('0.01'))
            annual_standard_deduction = INDIA_STANDARD_DEDUCTION
            annual_taxable_after_sd = calculate_taxable_income_with_investments(
                employee=employee,
                annual_gross=annual_taxable_gross,
                fiscal_year=fiscal_year,
                tax_regime=assignment.tax_regime,
            )
            annual_investment_deductions = max(
                ZERO,
                (calculate_taxable_income_after_standard_deduction(annual_taxable_gross) - annual_taxable_after_sd),
            ).quantize(Decimal('0.01'))
            annual_tax_breakdown = calculate_income_tax_with_rebate(
                taxable_income=annual_taxable_after_sd,
                tax_slab_set=tax_slab_set,
            )
            annual_tax_before_rebate = annual_tax_breakdown['tax_before_rebate']
            annual_rebate_87a = annual_tax_breakdown['rebate_87a']
            annual_tax_before_cess = annual_tax_breakdown['tax_after_rebate']
            annual_cess = annual_tax_breakdown['cess']
            annual_tax_total = annual_tax_breakdown['annual_tax']
            income_tax = (annual_tax_total / Decimal('12.00')).quantize(Decimal('0.01'))

            # ── Step 8: Final totals ─────────────────────────────────────────
            total_deductions = (employee_deductions + income_tax + lop_deduction).quantize(Decimal('0.01'))
            net_pay = ensure_non_negative_net_pay(gross_pay - total_deductions)

            PayrollRunItem.objects.create(
                pay_run=pay_run,
                employee=employee,
                status=PayrollRunItemStatus.READY,
                gross_pay=gross_pay.quantize(Decimal('0.01')),
                employee_deductions=employee_deductions.quantize(Decimal('0.01')),
                employer_contributions=employer_contributions.quantize(Decimal('0.01')),
                income_tax=income_tax,
                total_deductions=total_deductions,
                net_pay=net_pay,
                snapshot={
                    'assignment_id': str(assignment.id),
                    'tax_regime': assignment.tax_regime,
                    'tax_slab_set_id': str(tax_slab_set.id),
                    'readiness': _employee_payroll_snapshot(employee),
                    'lines': lines_snapshot,
                    'arrears': str(arrears_amount),
                    # Period detail
                    'period_start': str(period_start),
                    'period_end': str(period_end),
                    'paid_days': paid_days,
                    'attendance_paid_days': str(attendance_paid_days),
                    'total_days_in_period': total_days_in_period,
                    'pro_rate_factor': str(prorate_factor),
                    # Auto-calculated statutory
                    'auto_pf': str(auto_pf),
                    'esi_employee': str(esi_employee),
                    'esi_employer': str(esi_employer),
                    'pt_monthly': str(pt_monthly),
                    # LOP
                    'lop_days': str(lop_days),
                    'lop_deduction': str(lop_deduction),
                    'attendance_overtime_minutes': attendance_overtime_minutes,
                    'attendance': attendance_context,
                    # Tax working
                    'annual_taxable_gross': str(annual_taxable_gross),
                    'annual_standard_deduction': str(annual_standard_deduction),
                    'annual_investment_deductions': str(annual_investment_deductions),
                    'annual_taxable_after_sd': str(annual_taxable_after_sd),
                    'annual_tax_before_rebate': str(annual_tax_before_rebate),
                    'annual_rebate_87a': str(annual_rebate_87a),
                    'annual_tax_before_cess': str(annual_tax_before_cess),
                    'annual_cess': str(annual_cess),
                    'annual_tax_total': str(annual_tax_total),
                },
            )

        run_attendance_snapshot['total_attendance_paid_days'] = str(total_attendance_paid_days.quantize(Decimal('0.01')))
        run_attendance_snapshot['total_lop_days'] = str(total_lop_days.quantize(Decimal('0.01')))
        run_attendance_snapshot['total_overtime_minutes'] = total_overtime_minutes
        pay_run.attendance_snapshot = run_attendance_snapshot
        pay_run.status = PayrollRunStatus.CALCULATED
        pay_run.calculated_at = timezone.now()
        pay_run.submitted_at = None
        pay_run.save(update_fields=['attendance_snapshot', 'status', 'calculated_at', 'submitted_at', 'approval_run', 'modified_at'])

    log_audit_event(actor, 'payroll.run.calculated', organisation=pay_run.organisation, target=pay_run)
    return pay_run


def generate_form16_data(pay_run) -> dict:
    employees_data = []
    fiscal_year = _fiscal_year_for_period(pay_run.period_year, pay_run.period_month)
    for payslip in pay_run.payslips.select_related('employee__user').all():
        snapshot = payslip.snapshot or {}
        employee = payslip.employee
        pan_identifier = (
            employee.government_ids.filter(id_type=GovernmentIdType.PAN)
            .order_by('-created_at')
            .values_list('masked_identifier', flat=True)
            .first()
            or ''
        )
        tax_regime = snapshot.get('tax_regime', payslip.pay_run_item.snapshot.get('tax_regime', TaxRegime.NEW))
        employees_data.append(
            {
                'employee_id': str(employee.id),
                'employee_code': employee.employee_code or '',
                'employee_name': employee.user.full_name,
                'employee_pan': pan_identifier,
                'part_a': {
                    'employer_name': pay_run.organisation.name,
                    'employer_pan': pay_run.organisation.pan_number or '',
                    'certificate_period': f'{pay_run.period_month:02d}/{pay_run.period_year}',
                    'tax_deducted': snapshot.get('income_tax', '0'),
                    'tax_deposited': snapshot.get('income_tax', '0'),
                },
                'part_b': {
                    'opting_out_of_section_115bac_1a': 'YES' if tax_regime == TaxRegime.OLD else 'NO',
                    'gross_salary': snapshot.get('gross_pay', '0'),
                    'standard_deduction': snapshot.get('annual_standard_deduction', str(INDIA_STANDARD_DEDUCTION)),
                    'deductions_chapter_via': snapshot.get('annual_investment_deductions', '0'),
                    'total_taxable_income': snapshot.get('annual_taxable_after_sd', '0'),
                    'tax_on_total_income': snapshot.get('annual_tax_before_rebate', snapshot.get('annual_tax_before_cess', '0')),
                    'rebate_87a': snapshot.get('annual_rebate_87a', '0'),
                    'health_and_education_cess': snapshot.get('annual_cess', '0'),
                    'tax_payable': snapshot.get('annual_tax_total', '0'),
                },
            }
        )
    return {
        'pay_run_id': str(pay_run.id),
        'organisation': pay_run.organisation.name,
        'fiscal_year': fiscal_year,
        'employees': employees_data,
    }


def submit_pay_run_for_approval(pay_run, *, requester_user, requester_employee=None):
    if pay_run.status != PayrollRunStatus.CALCULATED:
        raise ValueError('Only calculated payroll runs can be submitted for approval.')
    exception_summary = _summarize_pay_run_exceptions(pay_run)
    if exception_summary:
        raise ValueError(exception_summary)
    if not pay_run.items.filter(status=PayrollRunItemStatus.READY).exists():
        raise ValueError('Calculate payroll successfully for at least one employee before submitting the run for approval.')
    organisation, requester_user, requester_employee = _resolve_payroll_requester_context(
        requester_user=requester_user,
        requester_employee=requester_employee,
        organisation=pay_run.organisation,
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
    pay_run.status = PayrollRunStatus.APPROVAL_PENDING
    pay_run.submitted_at = timezone.now()
    pay_run.save(update_fields=['approval_run', 'status', 'submitted_at', 'modified_at'])
    return pay_run


def finalize_pay_run(pay_run, *, actor=None, skip_approval=False):
    if pay_run.status not in [PayrollRunStatus.APPROVED, PayrollRunStatus.CALCULATED]:
        raise ValueError('Only approved or explicitly bypassed calculated payroll runs can be finalized.')
    if pay_run.status == PayrollRunStatus.CALCULATED and not skip_approval:
        raise ValueError('Approval is required before finalization.')
    exception_summary = _summarize_pay_run_exceptions(pay_run)
    if exception_summary:
        raise ValueError(exception_summary)
    if not pay_run.items.filter(status=PayrollRunItemStatus.READY).exists():
        raise ValueError('Calculate payroll successfully for at least one employee before finalization.')

    with transaction.atomic():
        for item in pay_run.items.select_related('employee__user').filter(status=PayrollRunItemStatus.READY):
            calc = item.snapshot  # carries all calculation detail from calculate_pay_run
            snapshot = {
                'employee_id': str(item.employee_id),
                'employee_name': item.employee.user.full_name,
                'employee_code': item.employee.employee_code or '',
                'period_year': pay_run.period_year,
                'period_month': pay_run.period_month,
                'period_label': date(pay_run.period_year, pay_run.period_month, 1).strftime('%B %Y'),
                'gross_pay': str(item.gross_pay),
                'employee_deductions': str(item.employee_deductions),
                'employer_contributions': str(item.employer_contributions),
                'income_tax': str(item.income_tax),
                'total_deductions': str(item.total_deductions),
                'net_pay': str(item.net_pay),
                'arrears': calc.get('arrears', '0'),
                'lines': calc.get('lines', []),
                # Period / pro-ration detail
                'paid_days': calc.get('paid_days', ''),
                'total_days_in_period': calc.get('total_days_in_period', ''),
                'pro_rate_factor': calc.get('pro_rate_factor', '1.00'),
                # LOP
                'lop_days': calc.get('lop_days', '0'),
                'lop_deduction': calc.get('lop_deduction', '0'),
                # Tax working
                'annual_taxable_gross': calc.get('annual_taxable_gross', ''),
                'annual_standard_deduction': calc.get('annual_standard_deduction', ''),
                'annual_taxable_after_sd': calc.get('annual_taxable_after_sd', ''),
                'annual_tax_before_cess': calc.get('annual_tax_before_cess', ''),
                'annual_cess': calc.get('annual_cess', ''),
                'annual_tax_total': calc.get('annual_tax_total', ''),
            }
            Payslip.objects.update_or_create(
                pay_run_item=item,
                defaults={
                    'organisation': pay_run.organisation,
                    'employee': item.employee,
                    'pay_run': pay_run,
                    'slip_number': f'{pay_run.period_year}{pay_run.period_month:02d}-{item.employee.employee_code or item.employee_id}',
                    'period_year': pay_run.period_year,
                    'period_month': pay_run.period_month,
                    'snapshot': snapshot,
                    'rendered_text': _build_rendered_payslip(snapshot),
                },
            )
            Arrears.objects.filter(
                employee=item.employee,
                pay_run=pay_run,
                is_included_in_payslip=False,
            ).update(is_included_in_payslip=True)

        pay_run.status = PayrollRunStatus.FINALIZED
        pay_run.finalized_at = timezone.now()
        pay_run.save(update_fields=['status', 'finalized_at', 'modified_at'])
        _notify_employees_payroll_finalized(pay_run, actor=actor)

    log_audit_event(actor, 'payroll.run.finalized', organisation=pay_run.organisation, target=pay_run)
    return pay_run


def rerun_payroll_run(pay_run, *, actor=None, requester_user=None, requester_employee=None):
    if pay_run.status != PayrollRunStatus.FINALIZED:
        raise ValueError('Only finalized payroll runs can be rerun.')
    new_run = create_payroll_run(
        pay_run.organisation,
        period_year=pay_run.period_year,
        period_month=pay_run.period_month,
        actor=actor,
        requester_user=requester_user,
        requester_employee=requester_employee,
        source_run=pay_run,
        run_type=PayrollRunType.RERUN,
    )
    log_audit_event(actor or requester_user, 'payroll.run.rerun_created', organisation=pay_run.organisation, target=new_run)
    return new_run
