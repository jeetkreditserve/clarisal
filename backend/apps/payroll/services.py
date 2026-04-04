# ruff: noqa: I001
from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal
import hashlib

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from apps.approvals.models import ApprovalRequestKind, ApprovalRun, ApprovalRunStatus
from apps.approvals.services import cancel_approval_run, get_default_workflow
from apps.audit.services import log_audit_event
from apps.employees.models import Employee, EmployeeStatus, GovernmentIdType
from apps.notifications.models import NotificationKind
from apps.notifications.services import create_notification
from apps.organisations.models import OrganisationAddressType

from .filings import fiscal_year_bounds, get_employee_identifier, quarter_months, stable_json
from .filings.ecr import generate_ecr_export
from .filings.esi import generate_esi_export
from .filings.form16 import generate_form16_pdf, generate_form16_xml
from .filings.form24q import generate_form24q_export
from .filings.professional_tax import generate_professional_tax_export
from .models import (
    Arrears,
    CompensationAssignment,
    CompensationAssignmentLine,
    CompensationAssignmentStatus,
    CompensationTemplate,
    CompensationTemplateLine,
    CompensationTemplateStatus,
    ESIEligibilityMode,
    FNFStatus,
    FullAndFinalSettlement,
    InvestmentDeclaration,
    InvestmentSection,
    LabourWelfareFundRule,
    PayrollComponent,
    PayrollComponentType,
    PayrollRun,
    PayrollRunItem,
    PayrollRunItemStatus,
    PayrollRunStatus,
    PayrollRunType,
    PayrollTDSChallan,
    PayrollTaxSlab,
    PayrollTaxSlabSet,
    Payslip,
    ProfessionalTaxGender,
    ProfessionalTaxRule,
    SECTION_LIMITS,
    StatutoryFilingArtifactFormat,
    StatutoryFilingBatch,
    StatutoryFilingStatus,
    StatutoryFilingType,
    StatutoryIncomeBasis,
    TaxRegime,
    tds_quarter_for_month,
)
from .statutory import (
    ESI_WAGE_CEILING,
    INDIA_STANDARD_DEDUCTION,
    PF_RATE,
    PF_WAGE_CEILING,
    calculate_epf_contributions,
    calculate_esi_contributions,
    calculate_fnf_salary_proration,
    calculate_gratuity_amount,
    calculate_gratuity_service_years,
    calculate_income_tax_with_rebate,
    calculate_labour_welfare_fund,
    calculate_leave_encashment_amount,
    calculate_taxable_income_after_standard_deduction,
    ensure_non_negative_net_pay,
    get_esi_contribution_period_bounds,
    surcharge_tiers_for_regime,
)

ZERO = Decimal('0.00')


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
    {'code': 'LWF_EMPLOYEE', 'name': 'Labour Welfare Fund (Employee)', 'component_type': PayrollComponentType.EMPLOYEE_DEDUCTION, 'is_taxable': False},
    {'code': 'LWF_EMPLOYER', 'name': 'Labour Welfare Fund (Employer)', 'component_type': PayrollComponentType.EMPLOYER_CONTRIBUTION, 'is_taxable': False},
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
    separator = '─' * 60
    thin_separator = '·' * 60

    def row(label, amount, indent=2):
        label_str = (' ' * indent) + label
        amount_str = _fmt_inr(amount)
        return f'{label_str:<44}{amount_str:>16}'

    period = snapshot.get('period_label', '')
    emp_name = snapshot.get('employee_name', '')
    paid_days = snapshot.get('paid_days', '')
    total_days = snapshot.get('total_days_in_period', '')

    out = [
        separator,
        f'{"PAYSLIP":^60}',
        f'{"Period: " + period:^60}',
        separator,
        f'  Employee : {emp_name}',
    ]
    if paid_days and total_days and str(paid_days) != str(total_days):
        out.append(f'  Paid Days: {paid_days} of {total_days} days')
    out.append(thin_separator)

    # Earnings section
    lines = snapshot.get('lines', [])
    earnings = [line for line in lines if line.get('component_type') == 'EARNING']
    if earnings:
        out.append('  EARNINGS')
        for e in earnings:
            out.append(row(e.get('component_name', ''), e.get('monthly_amount', '0')))
    arrears = snapshot.get('arrears', '0')
    try:
        if Decimal(str(arrears)) > ZERO:
            out.append(row('Arrears', arrears))
    except (ArithmeticError, TypeError, ValueError):
        arrears = ZERO
    out.append(row('Gross Salary', snapshot.get('gross_pay', '0')))
    out.append(thin_separator)

    # Deductions section
    emp_deductions = [
        line for line in lines
        if line.get('component_type') == 'EMPLOYEE_DEDUCTION'
        and line.get('component_code') not in ('', None)
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
    except (ArithmeticError, TypeError, ValueError):
        lop_deduction = ZERO

    # TDS line
    out.append(row('TDS (Income Tax)', snapshot.get('income_tax', '0')))
    out.append(row('Total Deductions', snapshot.get('total_deductions', '0')))
    out.append(thin_separator)

    # Employer contributions
    emp_contributions = [
        line for line in lines
        if line.get('component_type') == 'EMPLOYER_CONTRIBUTION'
        and line.get('component_code') not in ('', None)
    ]
    if emp_contributions:
        out.append('  EMPLOYER CONTRIBUTIONS  (not deducted from your pay)')
        for c in emp_contributions:
            label = c.get('component_name', '')
            if c.get('auto_calculated'):
                label += ' *'
            out.append(row(label, c.get('monthly_amount', '0')))
        out.append(thin_separator)

    # Tax computation detail
    ann_gross = snapshot.get('annual_taxable_gross')
    if ann_gross:
        out.append('  TAX COMPUTATION (Annual)')
        out.append(row('  Gross Taxable Income', ann_gross))
        out.append(row('  Less: Standard Deduction', snapshot.get('annual_standard_deduction', '0')))
        out.append(row('  Net Taxable Income', snapshot.get('annual_taxable_after_sd', '0')))
        out.append(row('  Income Tax (as per slabs)', snapshot.get('annual_tax_before_rebate', '0')))
        if Decimal(str(snapshot.get('annual_surcharge', '0'))) > ZERO:
            out.append(row('  Surcharge', snapshot.get('annual_surcharge', '0')))
        out.append(row('  Health & Education Cess (4%)', snapshot.get('annual_cess', '0')))
        out.append(row('  Total Annual Tax (TDS)', snapshot.get('annual_tax_total', '0')))
        out.append(thin_separator)

    # Net pay — prominent
    out.append(separator)
    net_str = _fmt_inr(snapshot.get('net_pay', '0'))
    out.append(f'  NET PAY (Take-Home){net_str:>40}')
    out.append(separator)
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


def _completed_service_years(date_of_joining, last_working_day):
    if date_of_joining is None or last_working_day is None or last_working_day < date_of_joining:
        return 0
    years = last_working_day.year - date_of_joining.year
    if (last_working_day.month, last_working_day.day) < (date_of_joining.month, date_of_joining.day):
        years -= 1
    return max(years, 0)


def _calculate_fnf_totals(employee, last_working_day, *, settlement=None):
    assignment = get_effective_compensation_assignment(employee, last_working_day)
    arrears = _normalize_decimal(getattr(settlement, 'arrears', ZERO)) or ZERO
    other_credits = _normalize_decimal(getattr(settlement, 'other_credits', ZERO)) or ZERO
    tds_deduction = _normalize_decimal(getattr(settlement, 'tds_deduction', ZERO)) or ZERO
    pf_deduction = _normalize_decimal(getattr(settlement, 'pf_deduction', ZERO)) or ZERO
    loan_recovery = _normalize_decimal(getattr(settlement, 'loan_recovery', ZERO)) or ZERO
    other_deductions = _normalize_decimal(getattr(settlement, 'other_deductions', ZERO)) or ZERO
    if assignment is None:
        gross_payable = (arrears + other_credits).quantize(Decimal('0.01'))
        net_payable = max(ZERO, gross_payable - tds_deduction - pf_deduction - loan_recovery - other_deductions).quantize(Decimal('0.01'))
        return {
            'prorated_salary': ZERO,
            'leave_encashment': ZERO,
            'gratuity': ZERO,
            'gross_payable': gross_payable,
            'net_payable': net_payable,
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
    gratuity = ZERO
    gratuity_service_years = calculate_gratuity_service_years(
        date_of_joining=employee.date_of_joining,
        last_working_day=last_working_day,
    )
    if _completed_service_years(employee.date_of_joining, last_working_day) >= 5:
        gratuity = calculate_gratuity_amount(
            last_basic_salary=monthly_basic_salary,
            years_of_service=gratuity_service_years,
        )
    gross_payable = (prorated_salary + leave_encashment + gratuity + arrears + other_credits).quantize(Decimal('0.01'))
    net_payable = max(ZERO, gross_payable - tds_deduction - pf_deduction - loan_recovery - other_deductions).quantize(Decimal('0.01'))
    return {
        'prorated_salary': prorated_salary,
        'leave_encashment': leave_encashment,
        'gratuity': gratuity,
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
            'gratuity': totals['gratuity'],
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
        totals = _calculate_fnf_totals(employee, last_working_day, settlement=fnf)
        for field_name in ('prorated_salary', 'leave_encashment', 'gratuity', 'gross_payable', 'net_payable'):
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
    from .statutory_seed import seed_statutory_master_data

    seed_statutory_master_data()
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


def assign_employee_compensation(
    employee,
    template,
    *,
    effective_from,
    actor=None,
    auto_approve=False,
    tax_regime=TaxRegime.NEW,
    is_pf_opted_out=False,
    vpf_rate_percent=Decimal('12.00'),
):
    normalized_vpf_rate_percent = Decimal('0.00') if is_pf_opted_out else Decimal(str(vpf_rate_percent)).quantize(Decimal('0.01'))
    if not is_pf_opted_out and normalized_vpf_rate_percent < Decimal('12.00'):
        raise ValueError('Employee PF/VPF rate cannot be below 12% unless PF is opted out.')
    if normalized_vpf_rate_percent > Decimal('100.00'):
        raise ValueError('Employee PF/VPF rate cannot exceed 100% of PF wages.')
    version = employee.compensation_assignments.count() + 1
    with transaction.atomic():
        assignment = CompensationAssignment.objects.create(
            employee=employee,
            template=template,
            effective_from=effective_from,
            version=version,
            tax_regime=tax_regime,
            is_pf_opted_out=is_pf_opted_out,
            vpf_rate_percent=normalized_vpf_rate_percent,
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


def _resolve_esi_eligibility(employee, *, gross_pay, period_year, period_month):
    contribution_period_start, contribution_period_end = get_esi_contribution_period_bounds(period_year, period_month)
    gross = _normalize_decimal(gross_pay) or ZERO
    qualifies_by_wage = gross <= ESI_WAGE_CEILING
    if qualifies_by_wage:
        return {
            'mode': ESIEligibilityMode.DIRECT,
            'force_eligible': False,
            'period_start': contribution_period_start,
            'period_end': contribution_period_end,
        }

    prior_window_coverage_exists = Payslip.objects.filter(
        employee=employee,
        esi_contribution_period_start=contribution_period_start,
        esi_contribution_period_end=contribution_period_end,
    ).exclude(esi_eligibility_mode=ESIEligibilityMode.NONE).exists()
    if prior_window_coverage_exists:
        return {
            'mode': ESIEligibilityMode.CONTINUED,
            'force_eligible': True,
            'period_start': contribution_period_start,
            'period_end': contribution_period_end,
        }
    return {
        'mode': ESIEligibilityMode.NONE,
        'force_eligible': False,
        'period_start': None,
        'period_end': None,
    }


def _resolve_organisation_payroll_state_code(organisation):
    active_addresses = organisation.addresses.filter(is_active=True)
    for address_type in (OrganisationAddressType.REGISTERED, OrganisationAddressType.BILLING):
        address = active_addresses.filter(address_type=address_type).order_by('created_at').first()
        if address and address.state_code:
            return address.state_code
    raise ValueError('No active registered or billing organisation address with a state code is configured for payroll.')


def _get_active_professional_tax_rule(state_code, *, as_of_date):
    return (
        ProfessionalTaxRule.objects.filter(
            country_code='IN',
            state_code=state_code,
            is_active=True,
            effective_from__lte=as_of_date,
        )
        .filter(Q(effective_to__isnull=True) | Q(effective_to__gte=as_of_date))
        .prefetch_related('slabs')
        .order_by('-effective_from', '-created_at')
        .first()
    )


def _resolve_professional_tax_amount(*, employee, state_code, gross_pay, period_year, period_month):
    rule = _get_active_professional_tax_rule(state_code, as_of_date=date(period_year, period_month, 1))
    if rule is None:
        raise ValueError(f'No active professional tax rule is configured for state {state_code}.')

    gross = _normalize_decimal(gross_pay) or ZERO
    if rule.income_basis == StatutoryIncomeBasis.HALF_YEARLY:
        taxable_basis = (gross * Decimal('6.00')).quantize(Decimal('0.01'))
    elif rule.income_basis == StatutoryIncomeBasis.ANNUAL:
        taxable_basis = (gross * Decimal('12.00')).quantize(Decimal('0.01'))
    else:
        taxable_basis = gross

    employee_gender = (getattr(getattr(employee, 'profile', None), 'gender', '') or '').upper()
    if employee_gender == ProfessionalTaxGender.FEMALE:
        gender_priority = [ProfessionalTaxGender.FEMALE, ProfessionalTaxGender.ANY, ProfessionalTaxGender.MALE]
    elif employee_gender == ProfessionalTaxGender.MALE:
        gender_priority = [ProfessionalTaxGender.MALE, ProfessionalTaxGender.ANY]
    else:
        gender_priority = [ProfessionalTaxGender.ANY, ProfessionalTaxGender.MALE, ProfessionalTaxGender.FEMALE]

    applicable_slabs = [
        slab
        for slab in rule.slabs.all()
        if not slab.applicable_months or period_month in slab.applicable_months
    ]
    for gender in gender_priority:
        for slab in applicable_slabs:
            if slab.gender != gender:
                continue
            if taxable_basis < slab.min_income:
                continue
            if slab.max_income is not None and taxable_basis > slab.max_income:
                continue
            return slab.deduction_amount.quantize(Decimal('0.01')), rule, taxable_basis
    return ZERO, rule, taxable_basis


def _get_active_labour_welfare_fund_rule(state_code, *, as_of_date):
    return (
        LabourWelfareFundRule.objects.filter(
            country_code='IN',
            state_code=state_code,
            is_active=True,
            effective_from__lte=as_of_date,
        )
        .filter(Q(effective_to__isnull=True) | Q(effective_to__gte=as_of_date))
        .prefetch_related('contributions')
        .order_by('-effective_from', '-created_at')
        .first()
    )


def _resolve_labour_welfare_fund_amount(*, state_code, gross_pay, period_year, period_month):
    rule = _get_active_labour_welfare_fund_rule(state_code, as_of_date=date(period_year, period_month, 1))
    gross = _normalize_decimal(gross_pay) or ZERO
    if rule is None:
        return calculate_labour_welfare_fund(
            state_code=state_code,
            payroll_month=period_month,
            gross_pay=gross,
            contributions=[],
        ), None, gross

    if rule.wage_basis == StatutoryIncomeBasis.HALF_YEARLY:
        wage_basis = (gross * Decimal('6.00')).quantize(Decimal('0.01'))
    elif rule.wage_basis == StatutoryIncomeBasis.ANNUAL:
        wage_basis = (gross * Decimal('12.00')).quantize(Decimal('0.01'))
    else:
        wage_basis = gross

    return (
        calculate_labour_welfare_fund(
            state_code=state_code,
            payroll_month=period_month,
            gross_pay=wage_basis,
            contributions=rule.contributions.all(),
        ),
        rule,
        wage_basis,
    )


def calculate_pay_run(pay_run, *, actor=None):
    if pay_run.status == PayrollRunStatus.APPROVED:
        raise ValueError('Approved payroll runs cannot be recalculated. Create a rerun or move the run back to draft first.')
    if pay_run.status == PayrollRunStatus.FINALIZED:
        raise ValueError('Finalized payroll runs cannot be recalculated.')
    if pay_run.approval_run_id and pay_run.approval_run.status == ApprovalRunStatus.PENDING:
        cancel_approval_run(pay_run.approval_run, actor=actor, subject_status=None)
        pay_run.approval_run = None

    period_start = date(pay_run.period_year, pay_run.period_month, 1)
    period_end = date(pay_run.period_year, pay_run.period_month, monthrange(pay_run.period_year, pay_run.period_month)[1])
    total_days_in_period = period_end.day
    fiscal_year = _fiscal_year_for_period(pay_run.period_year, pay_run.period_month)
    from apps.timeoff.models import LeaveRequest, LeaveRequestStatus
    try:
        org_state_code = _resolve_organisation_payroll_state_code(pay_run.organisation)
        org_state_resolution_error = None
    except ValueError as exc:
        org_state_code = None
        org_state_resolution_error = str(exc)

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
        ).select_related('user', 'office_location__organisation_address', 'profile')
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
            if org_state_resolution_error:
                PayrollRunItem.objects.create(
                    pay_run=pay_run,
                    employee=employee,
                    status=PayrollRunItemStatus.EXCEPTION,
                    message=org_state_resolution_error,
                    snapshot={'reason': org_state_resolution_error},
                )
                run_attendance_snapshot['exception_item_count'] += 1
                run_attendance_snapshot['employees'].append(
                    {
                        'employee_id': str(employee.id),
                        'employee_code': employee.employee_code or '',
                        'status': 'EXCEPTION',
                        'reason': org_state_resolution_error,
                    }
                )
                continue
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

            # ── Step 2: PF auto-calculation with wage ceiling, opt-out, and VPF ──
            auto_pf = ZERO
            pf_employer = ZERO
            pf_eligible_basic = ZERO
            pf_employee_rate_percent = assignment.vpf_rate_percent if not assignment.is_pf_opted_out else ZERO
            pf_is_opted_out = bool(
                assignment.is_pf_opted_out
                and basic_pay > PF_WAGE_CEILING
                and employee.date_of_joining is not None
            )
            if basic_pay > ZERO:
                pf_contributions = calculate_epf_contributions(
                    basic_pay=basic_pay,
                    employee_rate=ZERO if pf_is_opted_out else (pf_employee_rate_percent / Decimal('100.00')),
                    employer_rate=ZERO if pf_is_opted_out else PF_RATE,
                    wage_ceiling=PF_WAGE_CEILING,
                    cap_wages=True,
                )
                pf_eligible_basic = pf_contributions['eligible_basic']
                auto_pf = pf_contributions['employee']
                pf_employer = pf_contributions['employer']
                raw_employee_deductions += pf_contributions['employee']
                raw_employer_contributions += pf_contributions['employer']
                pf_employee_label = (
                    'Employee PF (Opted Out)'
                    if pf_is_opted_out
                    else f'Employee PF/VPF ({pf_employee_rate_percent}% of PF Wages)'
                )
                pf_employer_label = (
                    'Employer PF (Opted Out)'
                    if pf_is_opted_out
                    else f'Employer PF ({(PF_RATE * Decimal("100.00")).quantize(Decimal("0.01"))}% of PF Wages)'
                )
                # Update PF lines in snapshot with auto-calculated amounts
                for snap_line in lines_snapshot:
                    if snap_line.get('component_code') == 'PF_EMPLOYEE':
                        snap_line['monthly_amount'] = str(pf_contributions['employee'])
                        snap_line['component_name'] = pf_employee_label
                        snap_line['auto_calculated'] = True
                    elif snap_line.get('component_code') == 'PF_EMPLOYER':
                        snap_line['monthly_amount'] = str(pf_contributions['employer'])
                        snap_line['component_name'] = pf_employer_label
                        snap_line['auto_calculated'] = True
                if not has_pf_employee_line:
                    lines_snapshot.append({
                        'component_code': 'PF_EMPLOYEE',
                        'component_name': pf_employee_label,
                        'component_type': PayrollComponentType.EMPLOYEE_DEDUCTION,
                        'monthly_amount': str(pf_contributions['employee']),
                        'is_taxable': False,
                        'auto_calculated': True,
                    })
                if not has_pf_employer_line:
                    lines_snapshot.append({
                        'component_code': 'PF_EMPLOYER',
                        'component_name': pf_employer_label,
                        'component_type': PayrollComponentType.EMPLOYER_CONTRIBUTION,
                        'monthly_amount': str(pf_contributions['employer']),
                        'is_taxable': False,
                        'auto_calculated': True,
                    })

            # ── Step 3: ESI auto-calculation ─────────────────────────────────
            esi_employee = ZERO
            esi_employer = ZERO
            esi_eligibility = _resolve_esi_eligibility(
                employee,
                gross_pay=gross_pay,
                period_year=pay_run.period_year,
                period_month=pay_run.period_month,
            )
            esi_contributions = calculate_esi_contributions(
                gross_pay=gross_pay,
                force_eligible=esi_eligibility['force_eligible'],
            )
            if esi_contributions['is_applicable']:
                esi_employee = esi_contributions['employee']
                esi_employer = esi_contributions['employer']
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
            employee_state = org_state_code
            if (
                employee.office_location_id
                and employee.office_location.organisation_address_id
                and employee.office_location.organisation_address.state_code
            ):
                employee_state = employee.office_location.organisation_address.state_code
            try:
                pt_monthly, pt_rule, pt_taxable_basis = _resolve_professional_tax_amount(
                    employee=employee,
                    state_code=employee_state,
                    gross_pay=gross_pay,
                    period_year=pay_run.period_year,
                    period_month=pay_run.period_month,
                )
            except ValueError as exc:
                PayrollRunItem.objects.create(
                    pay_run=pay_run,
                    employee=employee,
                    status=PayrollRunItemStatus.EXCEPTION,
                    message=str(exc),
                    snapshot={'reason': str(exc), 'employee_state': employee_state or ''},
                )
                run_attendance_snapshot['exception_item_count'] += 1
                run_attendance_snapshot['employees'].append(
                    {
                        'employee_id': str(employee.id),
                        'employee_code': employee.employee_code or '',
                        'status': 'EXCEPTION',
                        'reason': str(exc),
                    }
                )
                continue
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

            # ── Step 4A: Labour Welfare Fund ────────────────────────────────
            lwf_employee = ZERO
            lwf_employer = ZERO
            lwf_rule = None
            lwf_wage_basis = gross_pay
            lwf_result, lwf_rule, lwf_wage_basis = _resolve_labour_welfare_fund_amount(
                state_code=employee_state,
                gross_pay=gross_pay,
                period_year=pay_run.period_year,
                period_month=pay_run.period_month,
            )
            if lwf_result['is_applicable']:
                lwf_employee = lwf_result['employee']
                lwf_employer = lwf_result['employer']
                raw_employee_deductions += lwf_employee
                raw_employer_contributions += lwf_employer
                lines_snapshot.append({
                    'component_code': 'LWF_EMPLOYEE',
                    'component_name': 'Labour Welfare Fund - Employee',
                    'component_type': PayrollComponentType.EMPLOYEE_DEDUCTION,
                    'monthly_amount': str(lwf_employee),
                    'is_taxable': False,
                    'auto_calculated': True,
                })
                lines_snapshot.append({
                    'component_code': 'LWF_EMPLOYER',
                    'component_name': 'Labour Welfare Fund - Employer',
                    'component_type': PayrollComponentType.EMPLOYER_CONTRIBUTION,
                    'monthly_amount': str(lwf_employer),
                    'is_taxable': False,
                    'auto_calculated': True,
                })

            employee_deductions = raw_employee_deductions
            employer_contributions = raw_employer_contributions

            # ── Step 5: Pro-ration for joining or exit month ─────────────────
            joining = employee.date_of_joining
            exit_date = employee.date_of_exit
            paid_period_start = joining if joining and period_start <= joining <= period_end else period_start
            paid_period_end = exit_date if exit_date and period_start <= exit_date < period_end else period_end
            paid_days = max(0, (paid_period_end - paid_period_start).days + 1)

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
                lwf_employee = (lwf_employee * prorate_factor).quantize(Decimal('0.01'))
                lwf_employer = (lwf_employer * prorate_factor).quantize(Decimal('0.01'))
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
                surcharge_tiers=surcharge_tiers_for_regime(assignment.tax_regime),
            )
            annual_tax_before_rebate = annual_tax_breakdown['tax_before_rebate']
            annual_rebate_87a = annual_tax_breakdown['rebate_87a']
            annual_surcharge = annual_tax_breakdown['surcharge']
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
                    'pf_employer': str(pf_employer),
                    'pf_eligible_basic': str(pf_eligible_basic),
                    'pf_employee_rate_percent': str(pf_employee_rate_percent),
                    'pf_is_opted_out': pf_is_opted_out,
                    'esi_employee': str(esi_employee),
                    'esi_employer': str(esi_employer),
                    'esi_eligibility_mode': esi_eligibility['mode'],
                    'esi_contribution_period_start': str(esi_eligibility['period_start']) if esi_eligibility['period_start'] else '',
                    'esi_contribution_period_end': str(esi_eligibility['period_end']) if esi_eligibility['period_end'] else '',
                    'pt_monthly': str(pt_monthly),
                    'pt_rule_id': str(pt_rule.id) if pt_rule else '',
                    'pt_state_code': employee_state or '',
                    'pt_taxable_basis': str(pt_taxable_basis),
                    'lwf_employee': str(lwf_employee),
                    'lwf_employer': str(lwf_employer),
                    'lwf_rule_id': str(lwf_rule.id) if lwf_rule else '',
                    'lwf_state_code': employee_state or '',
                    'lwf_wage_basis': str(lwf_wage_basis),
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
                    'annual_surcharge': str(annual_surcharge),
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
    challan = PayrollTDSChallan.objects.filter(
        organisation=pay_run.organisation,
        fiscal_year=fiscal_year,
        period_year=pay_run.period_year,
        period_month=pay_run.period_month,
        quarter=tds_quarter_for_month(pay_run.period_month),
    ).first()
    for payslip in pay_run.payslips.select_related('employee__user').all():
        snapshot = payslip.snapshot or {}
        employee = payslip.employee
        pan_identifier = get_employee_identifier(employee, id_type=GovernmentIdType.PAN)
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
                    'bsr_code': challan.bsr_code if challan else '',
                    'challan_serial_number': challan.challan_serial_number if challan else '',
                    'deposit_date': challan.deposit_date.isoformat() if challan else '',
                    'statement_receipt_number': challan.statement_receipt_number if challan else '',
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


def _filing_scope_filter(*, filing_type, period_year=None, period_month=None, fiscal_year='', quarter='', artifact_format=''):
    filters = {
        'filing_type': filing_type,
        'period_year': period_year,
        'period_month': period_month,
        'fiscal_year': fiscal_year or '',
        'quarter': quarter or '',
    }
    if artifact_format:
        filters['artifact_format'] = artifact_format
    return filters


def _finalized_runs_for_period(organisation, *, period_year: int, period_month: int):
    return list(
        PayrollRun.objects.filter(
            organisation=organisation,
            status=PayrollRunStatus.FINALIZED,
            period_year=period_year,
            period_month=period_month,
        ).order_by('period_year', 'period_month', 'finalized_at', 'created_at', 'id')
    )


def _finalized_runs_for_fiscal_year(organisation, *, fiscal_year: str):
    start_date, end_date = fiscal_year_bounds(fiscal_year)
    return list(
        PayrollRun.objects.filter(
            organisation=organisation,
            status=PayrollRunStatus.FINALIZED,
        )
        .filter(
            Q(period_year=start_date.year, period_month__gte=start_date.month)
            | Q(period_year=end_date.year, period_month__lte=end_date.month)
            | Q(period_year__gt=start_date.year, period_year__lt=end_date.year)
        )
        .order_by('period_year', 'period_month', 'finalized_at', 'created_at', 'id')
    )


def _finalized_runs_for_quarter(organisation, *, fiscal_year: str, quarter: str):
    month_pairs = quarter_months(fiscal_year, quarter)
    condition = Q()
    for year, month in month_pairs:
        condition |= Q(period_year=year, period_month=month)
    return list(
        PayrollRun.objects.filter(
            organisation=organisation,
            status=PayrollRunStatus.FINALIZED,
        )
        .filter(condition)
        .order_by('period_year', 'period_month', 'finalized_at', 'created_at', 'id')
    )


def _effective_payslips_for_runs(runs):
    if not runs:
        return []
    payslips = list(
        Payslip.objects.filter(pay_run__in=runs)
        .select_related('employee__user', 'employee__profile', 'pay_run', 'pay_run_item')
        .prefetch_related('employee__government_ids')
        .order_by('employee__employee_code', 'period_year', 'period_month', 'pay_run__finalized_at', 'created_at', 'id')
    )
    effective = {}
    for payslip in payslips:
        key = (str(payslip.employee_id), payslip.period_year, payslip.period_month)
        effective[key] = payslip
    return list(effective.values())


def _group_effective_payslips_by_employee(payslips):
    grouped = {}
    for payslip in sorted(payslips, key=lambda item: (item.employee.employee_code or '', item.period_year, item.period_month, str(item.id))):
        grouped.setdefault(str(payslip.employee_id), []).append(payslip)
    return grouped


def _source_signature(*, runs, payslips):
    signature_payload = {
        'runs': [
            {
                'id': str(run.id),
                'period_year': run.period_year,
                'period_month': run.period_month,
                'finalized_at': run.finalized_at.isoformat() if run.finalized_at else '',
            }
            for run in runs
        ],
        'payslips': [
            {
                'id': str(payslip.id),
                'employee_id': str(payslip.employee_id),
                'period_year': payslip.period_year,
                'period_month': payslip.period_month,
                'snapshot': payslip.snapshot,
            }
            for payslip in sorted(payslips, key=lambda item: (item.employee.employee_code or '', item.period_year, item.period_month, str(item.id)))
        ],
    }
    return hashlib.sha256(stable_json(signature_payload).encode('utf-8')).hexdigest()


def _apply_filing_batch_result(
    *,
    organisation,
    actor,
    filing_type,
    artifact_format,
    period_year=None,
    period_month=None,
    fiscal_year='',
    quarter='',
    runs,
    payslips,
    result,
    audit_action,
):
    batch = StatutoryFilingBatch.objects.create(
        organisation=organisation,
        filing_type=filing_type,
        artifact_format=artifact_format,
        period_year=period_year,
        period_month=period_month,
        fiscal_year=fiscal_year or '',
        quarter=quarter or '',
        status=StatutoryFilingStatus.BLOCKED if result.validation_errors else StatutoryFilingStatus.GENERATED,
        checksum=hashlib.sha256(result.payload_bytes()).hexdigest() if not result.validation_errors else '',
        file_name=result.file_name if not result.validation_errors else '',
        content_type=result.content_type if not result.validation_errors else '',
        file_size_bytes=len(result.payload_bytes()) if not result.validation_errors else 0,
        generated_at=timezone.now() if not result.validation_errors else None,
        source_signature=_source_signature(runs=runs, payslips=payslips),
        validation_errors=result.validation_errors,
        metadata=result.metadata | {'source_run_ids': [str(run.id) for run in runs]},
        structured_payload=result.structured_payload,
        artifact_text=result.artifact_text if not result.validation_errors else '',
        artifact_binary=result.artifact_binary if not result.validation_errors else None,
    )
    if runs:
        batch.source_pay_runs.set(runs)

    StatutoryFilingBatch.objects.filter(
        organisation=organisation,
        status__in=[
            StatutoryFilingStatus.READY,
            StatutoryFilingStatus.BLOCKED,
            StatutoryFilingStatus.GENERATED,
        ],
        **_filing_scope_filter(
            filing_type=filing_type,
            period_year=period_year,
            period_month=period_month,
            fiscal_year=fiscal_year,
            quarter=quarter,
            artifact_format=artifact_format,
        ),
    ).exclude(id=batch.id).update(status=StatutoryFilingStatus.SUPERSEDED, modified_at=timezone.now())

    log_audit_event(
        actor,
        audit_action,
        organisation=organisation,
        target=batch,
        payload={
            'filing_type': filing_type,
            'status': batch.status,
            'period_year': period_year,
            'period_month': period_month,
            'fiscal_year': fiscal_year,
            'quarter': quarter,
            'validation_errors': result.validation_errors,
            'checksum': batch.checksum,
            'file_name': batch.file_name,
        },
    )
    return batch


def list_statutory_filing_batches(organisation):
    return StatutoryFilingBatch.objects.filter(organisation=organisation).prefetch_related('source_pay_runs').order_by('-created_at')


def generate_statutory_filing_batch(
    organisation,
    *,
    filing_type,
    actor=None,
    period_year=None,
    period_month=None,
    fiscal_year='',
    quarter='',
    artifact_format='',
):
    filing_type = filing_type or ''
    fiscal_year = fiscal_year or ''
    quarter = quarter or ''
    artifact_format = artifact_format or ''

    if filing_type in {
        StatutoryFilingType.PF_ECR,
        StatutoryFilingType.ESI_MONTHLY,
        StatutoryFilingType.PROFESSIONAL_TAX,
    }:
        if not period_year or not period_month:
            raise ValueError('period_year and period_month are required for monthly filing exports.')
        runs = _finalized_runs_for_period(organisation, period_year=period_year, period_month=period_month)
        payslips = _effective_payslips_for_runs(runs)
        if not runs:
            result_factory = {
                StatutoryFilingType.PF_ECR: lambda: generate_ecr_export(organisation=organisation, payslips=[], period_year=period_year, period_month=period_month),
                StatutoryFilingType.ESI_MONTHLY: lambda: generate_esi_export(organisation=organisation, payslips=[], period_year=period_year, period_month=period_month),
                StatutoryFilingType.PROFESSIONAL_TAX: lambda: generate_professional_tax_export(organisation=organisation, payslips=[], period_year=period_year, period_month=period_month),
            }[filing_type]
            result = result_factory()
            result.validation_errors.append(f'No finalized payroll runs found for {period_month:02d}/{period_year}.')
        elif filing_type == StatutoryFilingType.PF_ECR:
            result = generate_ecr_export(organisation=organisation, payslips=payslips, period_year=period_year, period_month=period_month)
            artifact_format = StatutoryFilingArtifactFormat.CSV
        elif filing_type == StatutoryFilingType.ESI_MONTHLY:
            result = generate_esi_export(organisation=organisation, payslips=payslips, period_year=period_year, period_month=period_month)
            artifact_format = StatutoryFilingArtifactFormat.CSV
        else:
            result = generate_professional_tax_export(organisation=organisation, payslips=payslips, period_year=period_year, period_month=period_month)
            artifact_format = StatutoryFilingArtifactFormat.CSV
        return _apply_filing_batch_result(
            organisation=organisation,
            actor=actor,
            filing_type=filing_type,
            artifact_format=artifact_format or result.artifact_format,
            period_year=period_year,
            period_month=period_month,
            fiscal_year='',
            quarter='',
            runs=runs,
            payslips=payslips,
            result=result,
            audit_action='payroll.filing.generated',
        )

    if filing_type == StatutoryFilingType.FORM24Q:
        if not fiscal_year or not quarter:
            raise ValueError('fiscal_year and quarter are required for Form 24Q exports.')
        runs = _finalized_runs_for_quarter(organisation, fiscal_year=fiscal_year, quarter=quarter)
        payslips = _effective_payslips_for_runs(runs)
        grouped = _group_effective_payslips_by_employee(payslips)
        result = generate_form24q_export(organisation=organisation, quarter=quarter, fiscal_year=fiscal_year, payslips_by_employee=grouped)
        if not runs:
            result.validation_errors.append(f'No finalized payroll runs found for {quarter} of {fiscal_year}.')
        return _apply_filing_batch_result(
            organisation=organisation,
            actor=actor,
            filing_type=filing_type,
            artifact_format=StatutoryFilingArtifactFormat.JSON,
            fiscal_year=fiscal_year,
            quarter=quarter,
            runs=runs,
            payslips=payslips,
            result=result,
            audit_action='payroll.filing.generated',
        )

    if filing_type == StatutoryFilingType.FORM16:
        if not fiscal_year:
            raise ValueError('fiscal_year is required for Form 16 exports.')
        format_value = artifact_format or StatutoryFilingArtifactFormat.PDF
        runs = _finalized_runs_for_fiscal_year(organisation, fiscal_year=fiscal_year)
        payslips = _effective_payslips_for_runs(runs)
        grouped = _group_effective_payslips_by_employee(payslips)
        if format_value == StatutoryFilingArtifactFormat.XML:
            result = generate_form16_xml(organisation=organisation, fiscal_year=fiscal_year, payslips_by_employee=grouped)
        else:
            format_value = StatutoryFilingArtifactFormat.PDF
            result = generate_form16_pdf(organisation=organisation, fiscal_year=fiscal_year, payslips_by_employee=grouped)
        if not runs:
            result.validation_errors.append(f'No finalized payroll runs found for fiscal year {fiscal_year}.')
        return _apply_filing_batch_result(
            organisation=organisation,
            actor=actor,
            filing_type=filing_type,
            artifact_format=format_value,
            fiscal_year=fiscal_year,
            runs=runs,
            payslips=payslips,
            result=result,
            audit_action='payroll.filing.generated',
        )

    raise ValueError('Unsupported statutory filing type.')


def regenerate_statutory_filing_batch(batch, *, actor=None):
    regenerated = generate_statutory_filing_batch(
        batch.organisation,
        filing_type=batch.filing_type,
        actor=actor,
        period_year=batch.period_year,
        period_month=batch.period_month,
        fiscal_year=batch.fiscal_year,
        quarter=batch.quarter,
        artifact_format=batch.artifact_format,
    )
    log_audit_event(
        actor,
        'payroll.filing.regenerated',
        organisation=batch.organisation,
        target=regenerated,
        payload={'source_batch_id': str(batch.id), 'replacement_batch_id': str(regenerated.id)},
    )
    return regenerated


def cancel_statutory_filing_batch(batch, *, actor=None):
    if batch.status == StatutoryFilingStatus.CANCELLED:
        return batch
    batch.status = StatutoryFilingStatus.CANCELLED
    batch.save(update_fields=['status', 'modified_at'])
    log_audit_event(
        actor,
        'payroll.filing.cancelled',
        organisation=batch.organisation,
        target=batch,
        payload={'filing_type': batch.filing_type},
    )
    return batch


def download_statutory_filing_batch(batch, *, actor=None):
    if batch.status != StatutoryFilingStatus.GENERATED:
        raise ValueError('Only generated statutory filing batches can be downloaded.')
    log_audit_event(
        actor,
        'payroll.filing.downloaded',
        organisation=batch.organisation,
        target=batch,
        payload={'filing_type': batch.filing_type, 'file_name': batch.file_name},
    )
    if batch.artifact_binary:
        return bytes(batch.artifact_binary), batch.content_type, batch.file_name
    return batch.artifact_text.encode('utf-8'), batch.content_type, batch.file_name


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
                'annual_surcharge': calc.get('annual_surcharge', '0'),
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
                    'esi_contribution_period_start': calc.get('esi_contribution_period_start') or None,
                    'esi_contribution_period_end': calc.get('esi_contribution_period_end') or None,
                    'esi_eligibility_mode': calc.get('esi_eligibility_mode', ESIEligibilityMode.NONE),
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
